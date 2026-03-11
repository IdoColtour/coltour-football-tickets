import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from calendar import monthcalendar, month_name

# ============== GOOGLE SHEETS SETUP ==============
def init_google_sheets():
    """Initialize Google Sheets connection"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Try to load from secrets or environment
        if 'GOOGLE_SHEETS_CREDS' in st.secrets:
            creds_dict = st.secrets['GOOGLE_SHEETS_CREDS']
        elif os.path.exists('client_secret.json'):
            with open('client_secret.json') as f:
                creds_dict = json.load(f)
        else:
            st.warning("Google Sheets credentials not found. Running in local-only mode.")
            return None
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.warning(f"Google Sheets connection error: {e}")
        return None

# ============== PAGE CONFIG & STYLING ==============
st.set_page_config(
    page_title="🎫 ניהול כרטיסים PRO",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Football Tickets Management System v2.0"}
)

st.markdown("""
    <style>
    * { direction: rtl; text-align: right; }
    .main { background-color: #f8f9fa; }
    .stMetric { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .metric-label { font-size: 12px; opacity: 0.9; }
    .metric-value { font-size: 28px; font-weight: bold; margin-top: 5px; }
    .sold-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; 
                    border-radius: 4px; margin: 10px 0; }
    .seats-info { background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 10px; 
                  border-radius: 4px; font-size: 12px; margin-top: 5px; }
    .game-card { background: white; border-radius: 12px; padding: 20px; 
                 box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 15px 0; }
    .calendar-header { font-size: 20px; font-weight: bold; text-align: center; padding: 15px; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                       border-radius: 8px; margin-bottom: 15px; }
    .calendar-day { border: 1px solid #ddd; padding: 10px; height: 100px; 
                    border-radius: 6px; background: white; overflow-y: auto; }
    .calendar-event { background-color: #667eea; color: white; padding: 4px 8px; 
                      border-radius: 4px; font-size: 11px; margin-bottom: 3px; cursor: pointer; }
    .tab-container { background: white; border-radius: 12px; padding: 20px; 
                     box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .category-edit-box { background: #f0f2f6; padding: 15px; border-radius: 8px; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# ============== SESSION STATE INITIALIZATION ==============
if 'db' not in st.session_state:
    st.session_state.db = {
        'fixed_cats': {},  # {id: {name, qty, seats, created_at}}
        'games': [],       # [{id, name, date, cats: {name: {qty, seats}}}]
        'sales': []        # [{id, game_id, customer, email, qty, seat, cat, price, cost, total, game_name, game_date, created_at}]
    }

if 'google_sheets' not in st.session_state:
    st.session_state.google_sheets = init_google_sheets()

if 'show_add_game' not in st.session_state:
    st.session_state.show_add_game = False

db = st.session_state.db
gc = st.session_state.google_sheets

# ============== GOOGLE SHEETS SYNC FUNCTIONS ==============
def sync_to_sheets(sheet_name, data):
    """Sync data to Google Sheets"""
    if gc is None:
        return False
    try:
        sh = gc.open("ColtourTickets")
        ws = sh.worksheet(sheet_name)
        ws.clear()
        if data:
            ws.append_rows(data)
        return True
    except Exception as e:
        st.warning(f"Sync error: {e}")
        return False

def load_from_sheets(sheet_name):
    """Load data from Google Sheets"""
    if gc is None:
        return None
    try:
        sh = gc.open("ColtourTickets")
        ws = sh.worksheet(sheet_name)
        return ws.get_all_values()
    except Exception as e:
        st.warning(f"Load error: {e}")
        return None

def save_all_to_sheets():
    """Save all data to Google Sheets"""
    if gc is None:
        return
    
    # Convert fixed_cats to rows
    fixed_cats_rows = [['ID', 'Name', 'Qty', 'Seats', 'Created']]
    for cid, data in db['fixed_cats'].items():
        fixed_cats_rows.append([cid, data['name'], data['qty'], ','.join(data['seats']), data.get('created_at', '')])
    sync_to_sheets('FixedCategories', fixed_cats_rows)
    
    # Convert games to rows
    games_rows = [['ID', 'Name', 'Date', 'Categories']]
    for game in db['games']:
        games_rows.append([game['id'], game['name'], str(game['date']), json.dumps(game['cats'])])
    sync_to_sheets('Games', games_rows)
    
    # Convert sales to rows
    sales_rows = [['ID', 'GameID', 'Customer', 'Category', 'Seat', 'Price', 'Cost', 'Total', 'GameName', 'GameDate', 'CreatedAt']]
    for sale in db['sales']:
        sales_rows.append([
            sale.get('id', ''),
            sale['game_id'],
            sale['customer'],
            sale['cat'],
            sale.get('seat', ''),
            sale['price'],
            sale.get('cost', 0),
            sale['total'],
            sale['game_name'],
            str(sale['game_date']),
            sale['created_at']
        ])
    sync_to_sheets('Sales', sales_rows)

# ============== HELPER FUNCTIONS ==============
def get_game_sales(game_id):
    return [s for s in db['sales'] if s['game_id'] == game_id]

def get_category_stats(game_id, category_name):
    """Get sales and seat assignment stats for a category"""
    sales = [s for s in get_game_sales(game_id) if s['cat'] == category_name]
    sold_qty = len(sales)
    assigned_seats = len([s for s in sales if s.get('seat')])
    return {'sold': sold_qty, 'assigned': assigned_seats}

def get_available_seats(game_id, category_name):
    """Get list of unassigned seats for a category"""
    game = next((g for g in db['games'] if g['id'] == game_id), None)
    if not game or category_name not in game['cats']:
        return []
    
    all_seats = game['cats'][category_name]['seats']
    occupied = [s.get('seat', '') for s in get_game_sales(game_id) if s['cat'] == category_name and s.get('seat')]
    return [s for s in all_seats if s not in occupied and s]

# ============== SIDEBAR NAVIGATION ==============
st.sidebar.markdown("# 🎫 ניהול מערך כרטיסים")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "בחר דף:",
    ["📅 לוח שנה חדש", "🎮 יומן משחקים", "⚙️ קטגוריות קבועות", "📊 דוח מכירות", "💾 ייצוא/ייבוא"]
)

st.sidebar.markdown("---")
if st.sidebar.button("💾 שמור הכל ל-Google Sheets"):
    save_all_to_sheets()
    st.sidebar.success("✅ נשמר בהצלחה!")

# ============== PAGE 1: CALENDAR VIEW ==============
if menu == "📅 לוח שנה חדש":
    st.header("📅 לוח שנה ניהול משחקים")
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    
    if 'current_month' not in st.session_state:
        st.session_state.current_month = datetime.now()
    
    current_month = st.session_state.current_month
    
    with col_nav1:
        if st.button("⬅️ חודש קודם"):
            st.session_state.current_month = current_month - timedelta(days=current_month.day)
            st.rerun()
    
    with col_nav2:
        st.markdown(f"<div class='calendar-header'>{month_name[current_month.month]} {current_month.year}</div>", unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("חודש הבא ➡️"):
            st.session_state.current_month = current_month + timedelta(days=32)
            st.session_state.current_month = st.session_state.current_month.replace(day=1)
            st.rerun()
    
    # Display calendar grid
    cal = monthcalendar(current_month.year, current_month.month)
    
    # Days of week header
    days_header = st.columns(7)
    day_names = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
    for idx, day_name in enumerate(day_names):
        with days_header[idx]:
            st.markdown(f"<h4 style='text-align:center; color:#667eea;'>{day_name}</h4>", unsafe_allow_html=True)
    
    # Calendar days
    for week in cal:
        week_cols = st.columns(7)
        for day_idx, day in enumerate(week):
            with week_cols[day_idx]:
                if day == 0:
                    st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
                else:
                    date = datetime(current_month.year, current_month.month, day).date()
                    day_games = [g for g in db['games'] if g['date'] == date]
                    
                    st.markdown(f"<div class='calendar-day'>", unsafe_allow_html=True)
                    st.markdown(f"<b style='font-size:16px;'>{day}</b>")
                    
                    for game in day_games:
                        st.markdown(f"<div class='calendar-event'>{game['name']}</div>", unsafe_allow_html=True)
                    
                    if st.button("➕", key=f"add_game_{date}"):
                        st.session_state.selected_date = date
                        st.session_state.show_add_game = True
                        st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📌 סיכום חודש")
    total_games = len([g for g in db['games'] if g['date'].month == current_month.month and g['date'].year == current_month.year])
    total_sales = len([s for s in db['sales'] if datetime.strptime(s['created_at'][:10], '%Y-%m-%d').month == current_month.month])
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("משחקים בחודש", total_games)
    with col_stats2:
        st.metric("כרטיסים שנמכרו", total_sales)
    with col_stats3:
        total_revenue = sum([s['total'] for s in db['sales'] if datetime.strptime(s['created_at'][:10], '%Y-%m-%d').month == current_month.month])
        st.metric("הכנסות", f"₪{total_revenue:,.0f}")

# ============== PAGE 2: GAMES JOURNAL ==============
elif menu == "🎮 יומן משחקים":
    st.header("🎮 יומן ומעקב משחקים")
    
    col_date, col_btn = st.columns([3, 1])
    
    with col_date:
        selected_date = st.date_input("בחר תאריך לצפייה/הוספה", datetime.now())
    
    with col_btn:
        if st.button("➕ הוסף משחק", use_container_width=True):
            st.session_state.selected_date = selected_date
            st.session_state.show_add_game = True
    
    # Add new game form
    if st.session_state.get('show_add_game'):
        st.markdown("### ➕ משחק חדש")
        with st.form("new_game_form"):
            g_name = st.text_input("שם המשחק")
            
            col_fixed, col_extra = st.columns(2)
            
            with col_fixed:
                st.write("**קטגוריות קבועות להוספה:**")
                selected_fixed = st.multiselect(
                    "בחר קטגוריות",
                    options=list(db['fixed_cats'].keys()),
                    format_func=lambda x: f"{db['fixed_cats'][x]['name']} ({db['fixed_cats'][x]['qty']} כרטיסים)",
                    label_visibility="collapsed"
                )
            
            with col_extra:
                st.write("**קטגוריה חד-פעמית:**")
                extra_cat_name = st.text_input("שם קטגוריה", label_visibility="collapsed")
                extra_cat_qty = st.number_input("כמות כרטיסים", min_value=0, label_visibility="collapsed")
                extra_cat_seats = st.text_area("מקומות (מופרדים בפסיק)", label_visibility="collapsed")
                save_to_fixed = st.checkbox("שמור כקטגוריה קבועה")
            
            if st.form_submit_button("✅ צור משחק"):
                game_cats = {}
                
                # Add fixed categories
                for cid in selected_fixed:
                    f_cat = db['fixed_cats'][cid]
                    game_cats[f_cat['name']] = {"qty": f_cat['qty'], "seats": list(f_cat['seats'])}
                
                # Add one-time category
                if extra_cat_name:
                    s_list = [s.strip() for s in extra_cat_seats.split(",") if s.strip()] if extra_cat_seats else [str(i) for i in range(1, extra_cat_qty+1)]
                    game_cats[extra_cat_name] = {"qty": len(s_list), "seats": s_list}
                    
                    if save_to_fixed:
                        db['fixed_cats'][str(uuid.uuid4())[:8]] = {
                            "name": extra_cat_name,
                            "qty": len(s_list),
                            "seats": s_list,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                
                db['games'].append({
                    "id": str(uuid.uuid4())[:8],
                    "name": g_name,
                    "date": selected_date,
                    "cats": game_cats
                })
                
                st.session_state.show_add_game = False
                save_all_to_sheets()
                st.rerun()
    
    # Display games for selected date
    day_games = [g for g in db['games'] if g['date'] == selected_date]
    
    if not day_games:
        st.info("📌 אין משחקים רשומים לתאריך זה.")
    else:
        for game in day_games:
            with st.container():
                st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
                st.markdown(f"### 🏟️ {game['name']}")
                
                # Category stats dashboard
                st.write("**📊 סטטוס קטגוריות:**")
                cols = st.columns(len(game['cats']) if game['cats'] else 1)
                
                for idx, (c_name, c_data) in enumerate(game['cats'].items()):
                    stats = get_category_stats(game['id'], c_name)
                    with cols[idx]:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    color: white; padding: 15px; border-radius: 8px; text-align: center;'>
                            <div style='font-size: 24px; font-weight: bold;'>{stats['sold']}</div>
                            <div style='font-size: 12px; opacity: 0.9;'>כרטיסים נמכרו</div>
                            <div style='font-size: 11px; margin-top: 8px; opacity: 0.8;'>
                                {stats['assigned']} / {len([s for s in c_data['seats'] if s])} מקומות שנקבעו
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Tabs
                tab1, tab2, tab3, tab4 = st.tabs(["🛒 מכירה חדשה", "🪑 מפת מקומות", "✏️ ערוך קטגוריות", "🔄 הקצה מקומות"])
                
                with tab1:
                    st.write("**הוסף מכירה חדשה**")
                    with st.form(f"sale_{game['id']}"):
                        col_cat, col_qty = st.columns(2)
                        
                        with col_cat:
                            cat_sel = st.selectbox("קטגוריה", list(game['cats'].keys()), key=f"cat_{game['id']}")
                        
                        with col_qty:
                            c_qty = st.number_input("כמות כרטיסים", min_value=1, step=1, key=f"qty_{game['id']}")
                        
                        c_name = st.text_input("שם לקוח")
                        c_email = st.text_input("אימייל (אופציונלי)")
                        
                        col_price, col_cost = st.columns(2)
                        with col_price:
                            u_price = st.number_input("מחיר ליחידה", min_value=0, key=f"price_{game['id']}")
                        with col_cost:
                            u_cost = st.number_input("עלות ליחידה", min_value=0, key=f"cost_{game['id']}")
                        
                        # Seat assignment options
                        st.write("**הקצאת מקומות:**")
                        assign_now = st.checkbox("הקצה מקומות עכשיו", value=False)
                        
                        sel_seats = []
                        if assign_now:
                            available = get_available_seats(game['id'], cat_sel)
                            sel_seats = st.multiselect(f"בחר {c_qty} מקומות (יש {len(available)} פנויים)", available, key=f"seats_{game['id']}")
                        
                        if st.form_submit_button("✅ אשר מכירה"):
                            # Check if qty exceeds inventory
                            stats = get_category_stats(game['id'], cat_sel)
                            available_inv = game['cats'][cat_sel]['qty']
                            
                            if stats['sold'] + c_qty > available_inv:
                                st.warning(f"⚠️ זהירות: מכירה זו תחרוג מהמלאי ({stats['sold']} + {c_qty} > {available_inv})")
                            
                            if assign_now and len(sel_seats) != c_qty:
                                st.error(f"❌ עליך לבחור בדיוק {c_qty} מקומות!")
                            else:
                                # Create sale entry or multiple if seats are selected
                                if assign_now and sel_seats:
                                    for seat in sel_seats:
                                        db['sales'].append({
                                            "id": str(uuid.uuid4())[:8],
                                            "game_id": game['id'],
                                            "customer": c_name,
                                            "email": c_email,
                                            "cat": cat_sel,
                                            "qty": 1,
                                            "seat": seat,
                                            "price": u_price,
                                            "cost": u_cost,
                                            "total": u_price,
                                            "game_name": game['name'],
                                            "game_date": game['date'],
                                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                        })
                                else:
                                    # Create sale without seat assignment
                                    db['sales'].append({
                                        "id": str(uuid.uuid4())[:8],
                                        "game_id": game['id'],
                                        "customer": c_name,
                                        "email": c_email,
                                        "cat": cat_sel,
                                        "qty": c_qty,
                                        "seat": "",
                                        "price": u_price,
                                        "cost": u_cost,
                                        "total": u_price * c_qty,
                                        "game_name": game['name'],
                                        "game_date": game['date'],
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                    })
                                
                                save_all_to_sheets()
                                st.success("✅ המכירה בוצעה!")
                                st.rerun()
                
                with tab2:
                    cat_view = st.selectbox("ראה מקומות עבור:", list(game['cats'].keys()), key=f"view_{game['id']}")
                    seat_map = []
                    
                    for s in game['cats'][cat_view]['seats']:
                        if not s:
                            continue
                        owner = next((sl['customer'] for sl in get_game_sales(game['id']) if sl['cat'] == cat_view and sl['seat'] == s), "✅ פנוי")
                        status_color = "🔴 תפוס" if owner != "✅ פנוי" else "🟢 פנוי"
                        seat_map.append({"מקום": s, f"{status_color}": owner})
                    
                    if seat_map:
                        st.table(pd.DataFrame(seat_map))
                    else:
                        st.info("אין מקומות בקטגוריה זו.")
                
                with tab3:
                    st.warning("⚠️ שינויים כאן ישפיעו רק על המשחק הזה!")
                    for c_name, c_data in game['cats'].items():
                        st.markdown(f"<div class='category-edit-box'>", unsafe_allow_html=True)
                        st.write(f"**{c_name}**")
                        
                        new_qty = st.number_input(f"כמות כרטיסים", value=c_data['qty'], key=f"qty_edit_{game['id']}_{c_name}")
                        new_s = st.text_area(f"מקומות (מופרדים בפסיק)", ",".join(c_data['seats']), key=f"loc_edit_{game['id']}_{c_name}")
                        
                        if st.button(f"🔄 עדכן {c_name}", key=f"update_{game['id']}_{c_name}"):
                            seats_list = [x.strip() for x in new_s.split(",") if x.strip()]
                            game['cats'][c_name]['seats'] = seats_list
                            game['cats'][c_name]['qty'] = new_qty
                            save_all_to_sheets()
                            st.success("✅ עודכן!")
                            st.rerun()
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                
                with tab4:
                    st.write("**הקצה מקומות לכרטיסים ללא הקצאה**")
                    
                    # Find unassigned sales
                    unassigned_sales = [s for s in get_game_sales(game['id']) if not s.get('seat') or s['seat'] == '']
                    
                    if not unassigned_sales:
                        st.info("✅ כל הכרטיסים הוקצו!")
                    else:
                        for idx, sale in enumerate(unassigned_sales):
                            st.markdown(f"**{idx+1}. {sale['customer']} - {sale['cat']} ({sale['qty']} כרטיסים)**")
                            
                            available = get_available_seats(game['id'], sale['cat'])
                            
                            selected = st.multiselect(
                                f"בחר {sale['qty']} מקומות",
                                available,
                                key=f"assign_{sale['id']}"
                            )
                            
                            if st.button(f"✅ הקצה", key=f"btn_assign_{sale['id']}"):
                                if len(selected) != sale['qty']:
                                    st.error(f"בחר בדיוק {sale['qty']} מקומות!")
                                else:
                                    # Remove old sale and create new ones with seats
                                    db['sales'] = [s for s in db['sales'] if s['id'] != sale['id']]
                                    for seat in selected:
                                        db['sales'].append({
                                            "id": str(uuid.uuid4())[:8],
                                            "game_id": sale['game_id'],
                                            "customer": sale['customer'],
                                            "email": sale.get('email', ''),
                                            "cat": sale['cat'],
                                            "qty": 1,
                                            "seat": seat,
                                            "price": sale['price'],
                                            "cost": sale.get('cost', 0),
                                            "total": sale['price'],
                                            "game_name": sale['game_name'],
                                            "game_date": sale['game_date'],
                                            "created_at": sale['created_at']
                                        })
                                    save_all_to_sheets()
                                    st.success("✅ הוקצו!")
                                    st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

# ============== PAGE 3: FIXED CATEGORIES ==============
elif menu == "⚙️ קטגוריות קבועות":
    st.header("⚙️ הגדרת קטגוריות קבועות")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ הוסף קטגוריה חדשה", expanded=True):
            with st.form("add_fixed"):
                name = st.text_input("שם הקטגוריה")
                qty = st.number_input("כמות כרטיסים ברירת מחדל", min_value=1)
                seats = st.text_area("רשימת מקומות (מופרדים בפסיק) - אם ריק, יווצרו אוטומטית")
                
                if st.form_submit_button("💾 שמור במערכת"):
                    cat_id = str(uuid.uuid4())[:8]
                    seat_list = [s.strip() for s in seats.split(",")] if seats else [str(i) for i in range(1, qty+1)]
                    db['fixed_cats'][cat_id] = {
                        "name": name,
                        "qty": len(seat_list),
                        "seats": seat_list,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    save_all_to_sheets()
                    st.success("✅ הקטגוריה נוספה!")
                    st.rerun()
    
    with col2:
        st.metric("סה\"כ קטגוריות", len(db['fixed_cats']))
    
    if db['fixed_cats']:
        st.markdown("---")
        st.subheader("📋 רשימת קטגוריות קיימות")
        
        for cid, data in list(db['fixed_cats'].items()):
            with st.expander(f"🛠️ {data['name']} ({data['qty']} מקומות)", expanded=False):
                st.markdown(f"<div class='category-edit-box'>", unsafe_allow_html=True)
                
                new_name = st.text_input("שם הקטגוריה", data['name'], key=f"edit_n_{cid}")
                new_qty = st.number_input("כמות כרטיסים", value=data['qty'], min_value=1, key=f"edit_qty_{cid}")
                new_seats = st.text_area("מקומות (מופרדים בפסיק)", ",".join(data['seats']), key=f"edit_s_{cid}")
                
                col_upd, col_del = st.columns(2)
                
                with col_upd:
                    if st.button("✅ עדכן שינויים", key=f"upd_{cid}"):
                        seats_list = [s.strip() for s in new_seats.split(",") if s.strip()]
                        db['fixed_cats'][cid] = {
                            "name": new_name,
                            "qty": new_qty,
                            "seats": seats_list if seats_list else [str(i) for i in range(1, new_qty+1)],
                            "created_at": data.get('created_at', '')
                        }
                        save_all_to_sheets()
                        st.success("✅ עודכנה!")
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️ מחק קטגוריה", key=f"del_{cid}"):
                        del db['fixed_cats'][cid]
                        save_all_to_sheets()
                        st.success("✅ הוסרה!")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

# ============== PAGE 4: SALES REPORT ==============
elif menu == "📊 דוח מכירות":
    st.header("📊 דוח מכירות וביצועים")
    
    if db['sales']:
        # Aggregate sales (group by customer, game, category)
        aggregated = {}
        for sale in db['sales']:
            key = (sale['customer'], sale['cat'], sale['game_name'], sale['game_date'])
            if key not in aggregated:
                aggregated[key] = {
                    'customer': sale['customer'],
                    'category': sale['cat'],
                    'game': sale['game_name'],
                    'date': sale['game_date'],
                    'qty': 0,
                    'price_per_unit': sale['price'],
                    'total': 0,
                    'cost': 0,
                    'profit': 0,
                    'created_at': sale['created_at']
                }
            aggregated[key]['qty'] += sale['qty']
            aggregated[key]['total'] += sale['total']
            aggregated[key]['cost'] += sale.get('cost', 0) * sale['qty']
        
        # Convert to dataframe
        report_data = list(aggregated.values())
        for row in report_data:
            row['profit'] = row['total'] - row['cost']
        
        df = pd.DataFrame(report_data)
        df.columns = ['לקוח', 'קטגוריה', 'משחק', 'תאריך משחק', 'כמות', 'מחיר ליחידה', 'סה"כ שולם', 'עלות', 'רווח', 'תאריך מכירה']
        
        # Display metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("סה\"כ מכירות", len(db['sales']))
        with col_m2:
            st.metric("סה\"כ כרטיסים", df['כמות'].sum())
        with col_m3:
            st.metric("סה\"כ הכנסות", f"₪{df['סה\"כ שולם'].sum():,.0f}")
        with col_m4:
            st.metric("סה\"כ רווח", f"₪{df['רווח'].sum():,.0f}")
        
        st.markdown("---")
        
        # Filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            selected_game = st.multiselect("משחקים", df['משחק'].unique(), default=df['משחק'].unique())
        
        with col_filter2:
            selected_cat = st.multiselect("קטגוריות", df['קטגוריה'].unique(), default=df['קטגוריה'].unique())
        
        with col_filter3:
            sort_by = st.selectbox("מיין לפי", ['תאריך מכירה', 'סה"כ שולם', 'כמות'])
        
        # Apply filters
        df_filtered = df[
            (df['משחק'].isin(selected_game)) &
            (df['קטגוריה'].isin(selected_cat))
        ].sort_values(by=sort_by, ascending=False)
        
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Download options
        col_csv, col_json = st.columns(2)
        
        with col_csv:
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 ייצוא ל-CSV", csv, "sales_report.csv", "text/csv")
        
        with col_json:
            json_str = json.dumps(df_filtered.to_dict(orient='records'), ensure_ascii=False, indent=2).encode('utf-8')
            st.download_button("📥 ייצוא ל-JSON", json_str, "sales_report.json", "application/json")
    else:
        st.info("📭 אין נתוני מכירות להצגה עדיין.")

# ============== PAGE 5: IMPORT/EXPORT ==============
elif menu == "💾 ייצוא/ייבוא":
    st.header("💾 ייצוא וייבוא נתונים")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 ייצוא נתונים")
        
        export_format = st.radio("בחר פורמט", ["JSON", "CSV"])
        
        if st.button("ייצא נתונים"):
            if export_format == "JSON":
                export_data = {
                    'fixed_cats': db['fixed_cats'],
                    'games': db['games'],
                    'sales': db['sales']
                }
                json_str = json.dumps(export_data, ensure_ascii=False, indent=2, default=str).encode('utf-8')
                st.download_button("📥 הורד JSON", json_str, "coltour_backup.json", "application/json")
            else:
                # Sales to CSV
                if db['sales']:
                    df = pd.DataFrame(db['sales'])
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 הורד CSV", csv, "coltour_sales.csv", "text/csv")
                else:
                    st.warning("אין מכירות לייצא")
    
    with col2:
        st.subheader("📥 ייבוא נתונים")
        
        uploaded_file = st.file_uploader("בחר קובץ לייבוא", type=['json', 'csv'])
        
        if uploaded_file and st.button("ייבא נתונים"):
            try:
                if uploaded_file.name.endswith('.json'):
                    import_data = json.load(uploaded_file)
                    st.session_state.db = import_data
                    st.success("✅ נתונים יובאו בהצלחה!")
                else:
                    st.warning("⚠️ ייבוא CSV פשוט עדיין לא מומש. השתמש ב-JSON.")
            except Exception as e:
                st.error(f"❌ שגיאה: {e}")
    
    st.markdown("---")
    st.subheader("🔄 סנכרון Google Sheets")
    
    if st.button("💾 שמור הכל ל-Google Sheets"):
        save_all_to_sheets()
        st.success("✅ נשמר בהצלחה ל-Google Sheets!")
    
    if st.button("📥 טען מ-Google Sheets"):
        st.info("⏳ פונקציה זו תעמוד לרשות בעדכון הבא")
