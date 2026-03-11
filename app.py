import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import uuid
import json
from calendar import monthcalendar, month_name, weekday, MONDAY

# ============== PAGE CONFIG & STYLING ==============
st.set_page_config(
    page_title="🎫 Ticket Management System PRO",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    * { direction: ltr; text-align: left; }
    .main { background-color: #f8f9fa; }
    .stMetric { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .calendar-container { width: 100%; }
    .calendar-day-box { 
        border: 2px solid #ddd; 
        padding: 12px; 
        min-height: 140px; 
        border-radius: 8px; 
        background: white;
        position: relative;
        cursor: pointer;
    }
    .calendar-day-box:hover {
        background-color: #f0f2f6;
    }
    .calendar-day-box.empty {
        background: #f5f5f5;
        border: none;
        cursor: default;
    }
    .calendar-day-number {
        font-size: 16px;
        font-weight: bold;
        color: #667eea;
        margin-bottom: 8px;
    }
    .calendar-game-item {
        background-color: #667eea;
        color: white;
        padding: 6px;
        border-radius: 4px;
        font-size: 12px;
        margin-bottom: 4px;
        word-wrap: break-word;
        cursor: pointer;
    }
    .calendar-game-item:hover {
        background-color: #555;
    }
    .game-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 15px 0; }
    .category-edit-box { background: #f0f2f6; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .warning-box { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 4px; margin: 10px 0; }
    .sales-history { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# ============== SESSION STATE INITIALIZATION ==============
if 'db' not in st.session_state:
    st.session_state.db = {
        'fixed_cats': {},
        'fixed_teams': {},
        'games': [],
        'sales': []
    }

if 'show_add_game_form' not in st.session_state:
    st.session_state.show_add_game_form = False

if 'add_game_date' not in st.session_state:
    st.session_state.add_game_date = None

if 'current_month' not in st.session_state:
    st.session_state.current_month = datetime.now()

if 'view_game_id' not in st.session_state:
    st.session_state.view_game_id = None

if 'show_game_details' not in st.session_state:
    st.session_state.show_game_details = False

db = st.session_state.db

# ============== HELPER FUNCTIONS ==============
def get_game_sales(game_id):
    return [s for s in db['sales'] if s['game_id'] == game_id]

def get_category_stats(game_id, category_name):
    sales = [s for s in get_game_sales(game_id) if s['cat'] == category_name]
    sold_qty = sum([s['qty'] for s in sales])
    assigned_seats = len([s for s in sales if s.get('seat') and s['seat'] != ''])
    return {'sold': sold_qty, 'assigned': assigned_seats}

def get_available_seats(game_id, category_name):
    game = next((g for g in db['games'] if g['id'] == game_id), None)
    if not game or category_name not in game['cats']:
        return []
    
    all_seats = game['cats'][category_name]['seats']
    occupied = [s.get('seat', '') for s in get_game_sales(game_id) if s['cat'] == category_name and s.get('seat') and s['seat'] != '']
    return [s for s in all_seats if s not in occupied and s]

def get_unassigned_tickets(game_id, category_name):
    """Get unassigned sales for a category"""
    sales = [s for s in get_game_sales(game_id) if s['cat'] == category_name and (not s.get('seat') or s['seat'] == '')]
    return sales

def get_calendar_with_monday_start(year, month):
    """Get calendar with Monday as first day of week"""
    cal = monthcalendar(year, month)
    # monthcalendar returns weeks starting with Monday by default
    return cal

def display_game_details(game_id):
    """Display full game details"""
    game = next((g for g in db['games'] if g['id'] == game_id), None)
    if not game:
        return
    
    team_name = game.get('team', 'No Team')
    st.markdown(f"### 🏟️ {game['name']} - {game['date'].strftime('%B %d, %Y')} | Team: {team_name}")
    
    # Category stats dashboard
    st.write("**📊 Category Status:**")
    cols = st.columns(len(game['cats']) if game['cats'] else 1)
    
    for idx, (c_name, c_data) in enumerate(game['cats'].items()):
        stats = get_category_stats(game['id'], c_name)
        with cols[idx]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 15px; border-radius: 8px; text-align: center;'>
                <div style='font-size: 24px; font-weight: bold;'>{stats['sold']}</div>
                <div style='font-size: 12px; opacity: 0.9;'>Tickets Sold</div>
                <div style='font-size: 11px; margin-top: 8px; opacity: 0.8;'>
                    {stats['assigned']} / {len([s for s in c_data['seats'] if s])} Seats Assigned
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🛒 New Sale", "🪑 Seat Map", "✏️ Edit Categories", "🔄 Assign Seats", "📋 Sales History"])
    
    with tab1:
        st.write("**Add New Sale**")
        with st.form(f"sale_{game['id']}"):
            col_cat, col_qty = st.columns(2)
            
            with col_cat:
                cat_sel = st.selectbox("Category", list(game['cats'].keys()), key=f"cat_{game['id']}")
            
            with col_qty:
                c_qty = st.number_input("Quantity", min_value=1, step=1, key=f"qty_{game['id']}")
            
            c_name = st.text_input("Customer Name")
            c_email = st.text_input("Email (Optional)")
            
            col_price, col_cost = st.columns(2)
            with col_price:
                u_price = st.number_input("Price per Unit", min_value=0, key=f"price_{game['id']}")
            with col_cost:
                u_cost = st.number_input("Cost per Unit", min_value=0, key=f"cost_{game['id']}")
            
            st.write("**Seat Assignment:**")
            assign_now = st.checkbox("Assign Seats Now", value=False, key=f"assign_check_{game['id']}")
            
            sel_seats = []
            if assign_now:
                available = get_available_seats(game['id'], cat_sel)
                st.info(f"Available seats: {len(available)}")
                sel_seats = st.multiselect(f"Choose up to {c_qty} Seats", available, key=f"seats_{game['id']}")
            
            if st.form_submit_button("✅ Confirm Sale"):
                if not c_name:
                    st.error("Please enter customer name!")
                else:
                    stats = get_category_stats(game['id'], cat_sel)
                    available_inv = game['cats'][cat_sel]['qty']
                    
                    # Check for overselling
                    if stats['sold'] + c_qty > available_inv:
                        st.warning(f"⚠️ Warning: This sale EXCEEDS inventory ({stats['sold']} + {c_qty} > {available_inv}). You are overselling by {(stats['sold'] + c_qty) - available_inv} tickets.")
                    
                    if assign_now and len(sel_seats) > c_qty:
                        st.error(f"❌ Please select at most {c_qty} seats!")
                    else:
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
                            # If less seats than quantity, add remaining as unassigned
                            remaining = c_qty - len(sel_seats)
                            if remaining > 0:
                                db['sales'].append({
                                    "id": str(uuid.uuid4())[:8],
                                    "game_id": game['id'],
                                    "customer": c_name,
                                    "email": c_email,
                                    "cat": cat_sel,
                                    "qty": remaining,
                                    "seat": "",
                                    "price": u_price,
                                    "cost": u_cost,
                                    "total": u_price * remaining,
                                    "game_name": game['name'],
                                    "game_date": game['date'],
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                })
                        else:
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
                        
                        st.success("✅ Sale Recorded!")
                        st.rerun()
    
    with tab2:
        cat_view = st.selectbox("View Seats for:", list(game['cats'].keys()), key=f"view_{game['id']}")
        seat_map = []
        
        for s in game['cats'][cat_view]['seats']:
            if not s:
                continue
            owner = next((sl['customer'] for sl in get_game_sales(game['id']) if sl['cat'] == cat_view and sl['seat'] == s), "✅ Available")
            status_color = "🔴 Occupied" if owner != "✅ Available" else "🟢 Available"
            seat_map.append({"Seat": s, f"{status_color}": owner})
        
        if seat_map:
            st.table(pd.DataFrame(seat_map))
        else:
            st.info("No seats in this category.")
    
    with tab3:
        st.warning("⚠️ Changes here affect only this game!")
        
        col_add_cat = st.columns(1)
        with col_add_cat[0]:
            with st.expander("➕ Add New Category to This Game"):
                with st.form(f"add_cat_to_game_{game['id']}"):
                    col_fixed_sel, col_new_cat = st.columns(2)
                    
                    with col_fixed_sel:
                        st.write("**Select Fixed Category:**")
                        use_fixed = st.checkbox("Use Fixed Category", key=f"use_fixed_{game['id']}")
                        if use_fixed:
                            fixed_cat_options = [c for c in db['fixed_cats'].keys() if db['fixed_cats'][c]['name'] not in game['cats']]
                            if fixed_cat_options:
                                selected_fixed = st.selectbox("Choose Fixed Category", fixed_cat_options, 
                                                             format_func=lambda x: f"{db['fixed_cats'][x]['name']}", 
                                                             key=f"select_fixed_{game['id']}")
                            else:
                                st.info("All fixed categories already in this game")
                                selected_fixed = None
                        else:
                            selected_fixed = None
                    
                    with col_new_cat:
                        st.write("**Or Create New:**")
                        new_cat_name = st.text_input("Category Name", key=f"new_cat_name_{game['id']}")
                        new_cat_qty = st.number_input("Ticket Quantity", min_value=1, key=f"new_cat_qty_{game['id']}")
                        new_cat_seats = st.text_area("Seats (comma-separated) - Leave empty for empty seats", key=f"new_cat_seats_{game['id']}")
                        save_as_fixed = st.checkbox("Save as Fixed Category", key=f"save_as_fixed_{game['id']}")
                    
                    if st.form_submit_button("➕ Add Category"):
                        if use_fixed and selected_fixed:
                            f_cat = db['fixed_cats'][selected_fixed]
                            if f_cat['name'] in game['cats']:
                                st.error("Category already exists!")
                            else:
                                game['cats'][f_cat['name']] = {"qty": f_cat['qty'], "seats": list(f_cat['seats'])}
                                st.success("✅ Category Added!")
                                st.rerun()
                        elif new_cat_name:
                            if new_cat_name in game['cats']:
                                st.error("Category already exists!")
                            else:
                                if new_cat_seats:
                                    seats_list = [s.strip() for s in new_cat_seats.split(",") if s.strip()]
                                else:
                                    seats_list = ["" for _ in range(new_cat_qty)]
                                
                                game['cats'][new_cat_name] = {"qty": new_cat_qty, "seats": seats_list}
                                
                                if save_as_fixed:
                                    db['fixed_cats'][str(uuid.uuid4())[:8]] = {
                                        "name": new_cat_name,
                                        "team": game.get('team', ''),
                                        "qty": new_cat_qty,
                                        "seats": seats_list,
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                    }
                                
                                st.success("✅ Category Added!")
                                st.rerun()
                        else:
                            st.error("Please select or create a category!")
        
        st.markdown("---")
        
        for c_name, c_data in list(game['cats'].items()):
            st.markdown(f"<div class='category-edit-box'>", unsafe_allow_html=True)
            st.write(f"**{c_name}**")
            
            new_qty = st.number_input(f"Ticket Quantity", value=c_data['qty'], key=f"qty_edit_{game['id']}_{c_name}")
            new_name = st.text_input(f"Category Name", value=c_name, key=f"name_edit_{game['id']}_{c_name}")
            new_s = st.text_area(f"Seats (comma-separated)", ",".join(c_data['seats']), key=f"loc_edit_{game['id']}_{c_name}")
            
            col_upd, col_del = st.columns(2)
            
            with col_upd:
                if st.button(f"🔄 Update {c_name}", key=f"update_{game['id']}_{c_name}"):
                    seats_list = [x.strip() for x in new_s.split(",") if x.strip()] if new_s else ["" for _ in range(new_qty)]
                    if new_name != c_name and new_name in game['cats']:
                        st.error("Category name already exists!")
                    else:
                        if new_name != c_name:
                            game['cats'][new_name] = game['cats'].pop(c_name)
                            game['cats'][new_name]['seats'] = seats_list
                            game['cats'][new_name]['qty'] = new_qty
                        else:
                            game['cats'][c_name]['seats'] = seats_list
                            game['cats'][c_name]['qty'] = new_qty
                        st.success("✅ Updated!")
                        st.rerun()
            
            with col_del:
                if st.button(f"🗑️ Delete {c_name}", key=f"del_cat_{game['id']}_{c_name}"):
                    del game['cats'][c_name]
                    st.success("✅ Deleted!")
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    with tab4:
        st.write("**Assign Seats to Unassigned Tickets**")
        
        all_unassigned = []
        for cat_name in game['cats'].keys():
            unassigned_sales = get_unassigned_tickets(game['id'], cat_name)
            for sale in unassigned_sales:
                sale['category'] = cat_name
                all_unassigned.append(sale)
        
        if not all_unassigned:
            st.info("✅ All tickets have seats assigned or are not applicable!")
        else:
            for idx, sale in enumerate(all_unassigned):
                st.markdown(f"**{idx+1}. {sale['customer']} - {sale['category']} ({sale['qty']} tickets)**")
                
                available = get_available_seats(game['id'], sale['category'])
                
                selected = st.multiselect(
                    f"Choose up to {sale['qty']} Seats",
                    available,
                    key=f"assign_{sale['id']}"
                )
                
                if st.button(f"✅ Assign", key=f"btn_assign_{sale['id']}"):
                    if len(selected) > sale['qty']:
                        st.error(f"Please select at most {sale['qty']} seats!")
                    else:
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
                        # Add remaining unassigned
                        remaining = sale['qty'] - len(selected)
                        if remaining > 0:
                            db['sales'].append({
                                "id": str(uuid.uuid4())[:8],
                                "game_id": sale['game_id'],
                                "customer": sale['customer'],
                                "email": sale.get('email', ''),
                                "cat": sale['cat'],
                                "qty": remaining,
                                "seat": "",
                                "price": sale['price'],
                                "cost": sale.get('cost', 0),
                                "total": sale['price'] * remaining,
                                "game_name": sale['game_name'],
                                "game_date": sale['game_date'],
                                "created_at": sale['created_at']
                            })
                        st.success("✅ Seats Assigned!")
                        st.rerun()
    
    with tab5:
        st.write("**Sales History for This Game**")
        game_sales = get_game_sales(game['id'])
        
        if not game_sales:
            st.info("No sales yet for this game.")
        else:
            sales_list = []
            for idx, sale in enumerate(game_sales):
                sales_list.append({
                    '#': idx + 1,
                    'Customer': sale['customer'],
                    'Category': sale['cat'],
                    'Seat': sale.get('seat', 'Not Assigned') if sale.get('seat') else 'Not Assigned',
                    'Qty': sale['qty'],
                    'Price': f"${sale['price']}",
                    'Total': f"${sale['total']}",
                    'Date': sale['created_at']
                })
            
            df_sales = pd.DataFrame(sales_list)
            st.dataframe(df_sales, use_container_width=True, hide_index=True)

# ============== SIDEBAR NAVIGATION ==============
st.sidebar.markdown("# 🎫 Ticket Management System")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Select Page:",
    ["📅 Calendar View", "🎮 Games Journal", "⚙️ Fixed Categories", "🏆 Fixed Teams", "📊 Sales Report"]
)

st.sidebar.markdown("---")
st.sidebar.info("📱 All your data is safely stored in the app")

# ============== PAGE 1: CALENDAR VIEW ==============
if menu == "📅 Calendar View":
    st.header("📅 Calendar - Event Management")
    
    # Show game details if selected
    if st.session_state.show_game_details and st.session_state.view_game_id:
        with st.container():
            st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
            col_close = st.columns([10, 1])
            with col_close[1]:
                if st.button("❌ Close"):
                    st.session_state.show_game_details = False
                    st.session_state.view_game_id = None
                    st.rerun()
            display_game_details(st.session_state.view_game_id)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
    
    # Show add game form if needed
    if st.session_state.show_add_game_form and st.session_state.add_game_date:
        selected_date = st.session_state.add_game_date
        with st.container():
            st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
            st.subheader(f"➕ Add Game for {selected_date.strftime('%A, %B %d, %Y')}")
            
            with st.form("new_game_form_cal"):
                g_name = st.text_input("Game Name")
                
                col_team = st.columns(1)
                with col_team[0]:
                    st.write("**Team:**")
                    use_fixed_team = st.radio("Team Option", ["Select Fixed Team", "Add New Team"], key="cal_team_option", horizontal=True)
                    
                    if use_fixed_team == "Select Fixed Team":
                        team_options = list(db['fixed_teams'].keys())
                        if team_options:
                            selected_team = st.selectbox("Choose Team", team_options, format_func=lambda x: db['fixed_teams'][x], key="cal_select_team")
                            team_name = db['fixed_teams'][selected_team]
                        else:
                            st.info("No fixed teams yet. Create one in Fixed Teams section.")
                            team_name = ""
                    else:
                        team_name = st.text_input("New Team Name", key="cal_new_team")
                        save_team = st.checkbox("Save as Fixed Team", key="cal_save_team")
                
                col_fixed, col_extra = st.columns(2)
                
                with col_fixed:
                    st.write("**Fixed Categories:**")
                    selected_fixed = st.multiselect(
                        "Choose categories",
                        options=list(db['fixed_cats'].keys()),
                        format_func=lambda x: f"{db['fixed_cats'][x]['name']} ({db['fixed_cats'][x]['qty']} tickets)",
                        label_visibility="collapsed",
                        key="cal_fixed_cats"
                    )
                
                with col_extra:
                    st.write("**One-Time Category:**")
                    extra_cat_name = st.text_input("Category Name", label_visibility="collapsed", key="cal_extra_cat_name")
                    extra_cat_qty = st.number_input("Ticket Quantity", min_value=0, label_visibility="collapsed", key="cal_extra_qty")
                    save_to_fixed = st.checkbox("Save as Fixed Category", key="cal_save_fixed")
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.form_submit_button("✅ Create Game"):
                        if not g_name:
                            st.error("Please enter a game name!")
                        else:
                            # Save team if needed
                            if use_fixed_team == "Add New Team":
                                if not team_name:
                                    st.error("Please enter team name!")
                                else:
                                    if save_team and team_name not in db['fixed_teams'].values():
                                        db['fixed_teams'][str(uuid.uuid4())[:8]] = team_name
                            
                            game_cats = {}
                            
                            for cid in selected_fixed:
                                f_cat = db['fixed_cats'][cid]
                                game_cats[f_cat['name']] = {"qty": f_cat['qty'], "seats": list(f_cat['seats'])}
                            
                            if extra_cat_name:
                                seats_list = ["" for _ in range(extra_cat_qty)]
                                game_cats[extra_cat_name] = {"qty": extra_cat_qty, "seats": seats_list}
                                
                                if save_to_fixed:
                                    db['fixed_cats'][str(uuid.uuid4())[:8]] = {
                                        "name": extra_cat_name,
                                        "team": team_name,
                                        "qty": extra_cat_qty,
                                        "seats": seats_list,
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                    }
                            
                            db['games'].append({
                                "id": str(uuid.uuid4())[:8],
                                "name": g_name,
                                "date": selected_date,
                                "team": team_name,
                                "cats": game_cats
                            })
                            
                            st.session_state.show_add_game_form = False
                            st.session_state.add_game_date = None
                            st.success(f"✅ Game '{g_name}' added!")
                            st.rerun()
                
                with col_btn2:
                    if st.form_submit_button("❌ Cancel"):
                        st.session_state.show_add_game_form = False
                        st.session_state.add_game_date = None
                        st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("---")
    
    current_month = st.session_state.current_month
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    
    with col_nav1:
        if st.button("⬅️ Previous"):
            first_day = current_month.replace(day=1)
            st.session_state.current_month = first_day - timedelta(days=1)
            st.rerun()
    
    with col_nav2:
        month_year = f"{month_name[current_month.month]} {current_month.year}"
        st.markdown(f"<div style='text-align: center; font-size: 24px; font-weight: bold; color: #667eea;'>{month_year}</div>", unsafe_allow_html=True)
    
    with col_nav3:
        if st.button("Next ➡️"):
            last_day = current_month.replace(day=28) + timedelta(days=4)
            st.session_state.current_month = last_day.replace(day=1)
            st.rerun()
    
    # Get calendar for current month with Monday as first day
    cal = get_calendar_with_monday_start(current_month.year, current_month.month)
    
    # Display day names (Monday first)
    day_cols = st.columns(7)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for col_idx, day_name in enumerate(day_names):
        with day_cols[col_idx]:
            st.markdown(f"<h4 style='text-align: center; color: #667eea;'>{day_name}</h4>", unsafe_allow_html=True)
    
    # Display calendar days
    for week_idx, week in enumerate(cal):
        day_cols = st.columns(7)
        
        for day_col_idx, day in enumerate(week):
            with day_cols[day_col_idx]:
                if day == 0:
                    st.markdown("<div class='calendar-day-box empty'></div>", unsafe_allow_html=True)
                else:
                    date = datetime(current_month.year, current_month.month, day).date()
                    day_games = [g for g in db['games'] if g['date'] == date]
                    
                    # Create day content as text to avoid button HTML rendering issues
                    st.write(f"**{day}**")
                    
                    for game in day_games:
                        st.write(f"📌 {game['name']}")
                    
                    # Add buttons
                    col_btn_add, col_btn_view = st.columns(2)
                    
                    with col_btn_add:
                        if st.button("➕", key=f"add_btn_{date}"):
                            st.session_state.add_game_date = date
                            st.session_state.show_add_game_form = True
                            st.rerun()
                    
                    with col_btn_view:
                        if day_games:
                            if st.button("👁️", key=f"view_btn_{day_games[0]['id']}"):
                                st.session_state.view_game_id = day_games[0]['id']
                                st.session_state.show_game_details = True
                                st.rerun()
    
    st.markdown("---")
    
    # Month summary
    st.subheader("📌 Month Summary")
    
    total_games = len([g for g in db['games'] if g['date'].month == current_month.month and g['date'].year == current_month.year])
    total_sales = len([s for s in db['sales'] if datetime.strptime(s['created_at'][:10], '%Y-%m-%d').month == current_month.month])
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Games This Month", total_games)
    with col_stats2:
        st.metric("Tickets Sold", total_sales)
    with col_stats3:
        total_revenue = sum([s['total'] for s in db['sales'] if datetime.strptime(s['created_at'][:10], '%Y-%m-%d').month == current_month.month])
        st.metric("Revenue", f"${total_revenue:,.0f}")

# ============== PAGE 2: GAMES JOURNAL ==============
elif menu == "🎮 Games Journal":
    st.header("🎮 Games Journal & Tracking")
    
    view_mode = st.radio("View Mode:", ["By Date", "List View"])
    
    if view_mode == "By Date":
        col_date, col_btn = st.columns([3, 1])
        
        with col_date:
            selected_date = st.date_input("Select date to view/add games", datetime.now())
        
        with col_btn:
            if st.button("➕ Add Game", use_container_width=True):
                st.session_state.show_add_game_form = True
                st.session_state.add_game_date = selected_date
        
        # Add new game form
        if st.session_state.show_add_game_form and st.session_state.add_game_date == selected_date:
            with st.container():
                st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
                st.markdown("### ➕ Create New Game")
                with st.form("new_game_form_journal"):
                    g_name = st.text_input("Game Name")
                    
                    col_team = st.columns(1)
                    with col_team[0]:
                        st.write("**Team:**")
                        use_fixed_team = st.radio("Team Option", ["Select Fixed Team", "Add New Team"], key="journal_team_option", horizontal=True)
                        
                        if use_fixed_team == "Select Fixed Team":
                            team_options = list(db['fixed_teams'].keys())
                            if team_options:
                                selected_team = st.selectbox("Choose Team", team_options, format_func=lambda x: db['fixed_teams'][x], key="journal_select_team")
                                team_name = db['fixed_teams'][selected_team]
                            else:
                                st.info("No fixed teams yet. Create one in Fixed Teams section.")
                                team_name = ""
                        else:
                            team_name = st.text_input("New Team Name", key="journal_new_team")
                            save_team = st.checkbox("Save as Fixed Team", key="journal_save_team")
                    
                    col_fixed, col_extra = st.columns(2)
                    
                    with col_fixed:
                        st.write("**Fixed Categories to Add:**")
                        selected_fixed = st.multiselect(
                            "Choose categories",
                            options=list(db['fixed_cats'].keys()),
                            format_func=lambda x: f"{db['fixed_cats'][x]['name']} ({db['fixed_cats'][x]['qty']} tickets)",
                            label_visibility="collapsed",
                            key="journal_fixed_cats"
                        )
                    
                    with col_extra:
                        st.write("**One-Time Category:**")
                        extra_cat_name = st.text_input("Category Name", label_visibility="collapsed", key="journal_extra_cat_name")
                        extra_cat_qty = st.number_input("Ticket Quantity", min_value=0, label_visibility="collapsed", key="journal_extra_qty")
                        save_to_fixed = st.checkbox("Save as Fixed Category", key="journal_save_fixed")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.form_submit_button("✅ Create Game"):
                            if not g_name:
                                st.error("Please enter a game name!")
                            else:
                                # Save team if needed
                                if use_fixed_team == "Add New Team":
                                    if not team_name:
                                        st.error("Please enter team name!")
                                    else:
                                        if save_team and team_name not in db['fixed_teams'].values():
                                            db['fixed_teams'][str(uuid.uuid4())[:8]] = team_name
                                
                                game_cats = {}
                                
                                for cid in selected_fixed:
                                    f_cat = db['fixed_cats'][cid]
                                    game_cats[f_cat['name']] = {"qty": f_cat['qty'], "seats": list(f_cat['seats'])}
                                
                                if extra_cat_name:
                                    seats_list = ["" for _ in range(extra_cat_qty)]
                                    game_cats[extra_cat_name] = {"qty": extra_cat_qty, "seats": seats_list}
                                    
                                    if save_to_fixed:
                                        db['fixed_cats'][str(uuid.uuid4())[:8]] = {
                                            "name": extra_cat_name,
                                            "team": team_name,
                                            "qty": extra_cat_qty,
                                            "seats": seats_list,
                                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                        }
                                
                                db['games'].append({
                                    "id": str(uuid.uuid4())[:8],
                                    "name": g_name,
                                    "date": selected_date,
                                    "team": team_name,
                                    "cats": game_cats
                                })
                                
                                st.session_state.show_add_game_form = False
                                st.success("✅ Game Created!")
                                st.rerun()
                    
                    with col_btn2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state.show_add_game_form = False
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("---")
        
        # Display games for selected date
        day_games = [g for g in db['games'] if g['date'] == selected_date]
        
        if not day_games:
            st.info("📌 No games scheduled for this date.")
        else:
            for game in day_games:
                with st.container():
                    st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
                    display_game_details(game['id'])
                    st.markdown("</div>", unsafe_allow_html=True)
    
    else:  # List View
        st.subheader("All Games")
        
        if db['games']:
            games_list = []
            for game in sorted(db['games'], key=lambda x: x['date'], reverse=True):
                games_list.append({
                    '#': len(games_list) + 1,
                    'Game Name': game['name'],
                    'Team': game.get('team', 'No Team'),
                    'Date': game['date'].strftime('%B %d, %Y'),
                    'Categories': len(game['cats']),
                    'Sales': len(get_game_sales(game['id']))
                })
            
            df_games = pd.DataFrame(games_list)
            st.dataframe(df_games, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("View Game Details")
            game_names = [g['name'] for g in db['games']]
            selected_game_name = st.selectbox("Select a game", game_names)
            
            if selected_game_name:
                selected_game = next((g for g in db['games'] if g['name'] == selected_game_name), None)
                if selected_game:
                    with st.container():
                        st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
                        display_game_details(selected_game['id'])
                        st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("📌 No games created yet.")

# ============== PAGE 3: FIXED CATEGORIES ==============
elif menu == "⚙️ Fixed Categories":
    st.header("⚙️ Manage Fixed Categories")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ Add New Category", expanded=True):
            with st.form("add_fixed"):
                name = st.text_input("Category Name")
                team = st.text_input("Team/Club (Optional)")
                qty = st.number_input("Ticket Quantity", min_value=1)
                seats_input = st.text_area("Seat List (comma-separated) - Leave empty to create empty seats")
                
                if st.form_submit_button("💾 Save Category"):
                    if not name:
                        st.error("Please enter a category name!")
                    else:
                        cat_id = str(uuid.uuid4())[:8]
                        if seats_input:
                            seat_list = [s.strip() for s in seats_input.split(",") if s.strip()]
                        else:
                            seat_list = ["" for _ in range(qty)]
                        
                        db['fixed_cats'][cat_id] = {
                            "name": name,
                            "team": team,
                            "qty": qty,
                            "seats": seat_list,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        st.success("✅ Category Added!")
                        st.rerun()
    
    with col2:
        st.metric("Total Categories", len(db['fixed_cats']))
    
    if db['fixed_cats']:
        st.markdown("---")
        st.subheader("📋 Existing Categories")
        
        for cid, data in list(db['fixed_cats'].items()):
            team_info = f" - {data.get('team', '')}" if data.get('team') else ""
            with st.expander(f"🛠️ {data['name']}{team_info} ({data['qty']} seats)", expanded=False):
                st.markdown(f"<div class='category-edit-box'>", unsafe_allow_html=True)
                
                new_name = st.text_input("Category Name", data['name'], key=f"edit_n_{cid}")
                new_team = st.text_input("Team/Club", data.get('team', ''), key=f"edit_team_{cid}")
                new_qty = st.number_input(f"Ticket Quantity", value=data['qty'], min_value=1, key=f"edit_qty_{cid}")
                new_seats = st.text_area("Seats (comma-separated)", ",".join(data['seats']), key=f"edit_s_{cid}")
                
                col_upd, col_del = st.columns(2)
                
                with col_upd:
                    if st.button("✅ Update Changes", key=f"upd_{cid}"):
                        if new_seats:
                            seats_list = [s.strip() for s in new_seats.split(",") if s.strip()]
                        else:
                            seats_list = ["" for _ in range(new_qty)]
                        
                        db['fixed_cats'][cid] = {
                            "name": new_name,
                            "team": new_team,
                            "qty": new_qty,
                            "seats": seats_list,
                            "created_at": data.get('created_at', '')
                        }
                        st.success("✅ Updated!")
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️ Delete Category", key=f"del_{cid}"):
                        del db['fixed_cats'][cid]
                        st.success("✅ Removed!")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

# ============== PAGE 4: FIXED TEAMS ==============
elif menu == "🏆 Fixed Teams":
    st.header("🏆 Manage Fixed Teams")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ Add New Team", expanded=True):
            with st.form("add_team"):
                team_name = st.text_input("Team Name")
                team_city = st.text_input("City (Optional)")
                
                if st.form_submit_button("💾 Save Team"):
                    if not team_name:
                        st.error("Please enter a team name!")
                    else:
                        team_id = str(uuid.uuid4())[:8]
                        db['fixed_teams'][team_id] = team_name
                        st.success("✅ Team Added!")
                        st.rerun()
    
    with col2:
        st.metric("Total Teams", len(db['fixed_teams']))
    
    if db['fixed_teams']:
        st.markdown("---")
        st.subheader("📋 Existing Teams")
        
        for tid, team_name in list(db['fixed_teams'].items()):
            with st.expander(f"🏆 {team_name}", expanded=False):
                st.markdown(f"<div class='category-edit-box'>", unsafe_allow_html=True)
                
                new_name = st.text_input("Team Name", team_name, key=f"edit_team_{tid}")
                
                col_upd, col_del = st.columns(2)
                
                with col_upd:
                    if st.button("✅ Update Name", key=f"upd_team_{tid}"):
                        db['fixed_teams'][tid] = new_name
                        st.success("✅ Updated!")
                        st.rerun()
                
                with col_del:
                    if st.button("🗑️ Delete Team", key=f"del_team_{tid}"):
                        del db['fixed_teams'][tid]
                        st.success("✅ Removed!")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

# ============== PAGE 5: SALES REPORT ==============
elif menu == "📊 Sales Report":
    st.header("📊 Sales Report & Performance")
    
    if db['sales']:
        # Date range filter
        st.subheader("Filter by Date Range")
        col_date1, col_date2, col_all = st.columns([2, 2, 1])
        
        with col_all:
            show_all = st.checkbox("Show All Dates", value=True)
        
        if show_all:
            filtered_sales = db['sales']
        else:
            with col_date1:
                start_date = st.date_input("Start Date", datetime.now().replace(day=1))
            with col_date2:
                end_date = st.date_input("End Date", datetime.now())
            
            filtered_sales = [s for s in db['sales'] 
                            if start_date <= datetime.strptime(s['game_date'].strftime('%Y-%m-%d'), '%Y-%m-%d').date() <= end_date]
        
        # Aggregate sales
        aggregated = {}
        for sale in filtered_sales:
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
        
        report_data = list(aggregated.values())
        for row in report_data:
            row['profit'] = row['total'] - row['cost']
        
        df = pd.DataFrame(report_data)
        df.columns = ['Customer', 'Category', 'Game', 'Game Date', 'Quantity', 'Price/Unit', 'Total Paid', 'Cost', 'Profit', 'Sale Date']
        
        # Display metrics
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total Sales", len(filtered_sales))
        with col_m2:
            st.metric("Total Tickets", df['Quantity'].sum())
        with col_m3:
            st.metric("Total Revenue", f"${df['Total Paid'].sum():,.0f}")
        with col_m4:
            st.metric("Total Profit", f"${df['Profit'].sum():,.0f}")
        
        st.markdown("---")
        
        # Filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            selected_game = st.multiselect("Games", df['Game'].unique(), default=df['Game'].unique())
        
        with col_filter2:
            selected_cat = st.multiselect("Categories", df['Category'].unique(), default=df['Category'].unique())
        
        with col_filter3:
            sort_by = st.selectbox("Sort By", ['Sale Date', 'Total Paid', 'Quantity'])
        
        df_filtered = df[
            (df['Game'].isin(selected_game)) &
            (df['Category'].isin(selected_cat))
        ].sort_values(by=sort_by, ascending=False)
        
        # Add numbering
        df_filtered_display = df_filtered.copy()
        df_filtered_display.insert(0, '#', range(1, len(df_filtered_display) + 1))
        
        st.dataframe(df_filtered_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Download
        col_csv, col_json = st.columns(2)
        
        with col_csv:
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Export to CSV", csv, "sales_report.csv", "text/csv")
        
        with col_json:
            json_str = json.dumps(df_filtered.to_dict(orient='records'), ensure_ascii=False, indent=2).encode('utf-8')
            st.download_button("📥 Export to JSON", json_str, "sales_report.json", "application/json")
    else:
        st.info("📭 No sales data to display yet.")
