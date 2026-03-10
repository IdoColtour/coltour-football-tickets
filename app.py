import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
import uuid

# --- הגדרות עיצוב RTL ודאשבורד ---
st.set_page_config(page_title="Football Ticket Manager PRO", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 5px; }
    .game-card { border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; margin-bottom: 10px; background: #ffffff; box-shadow: 2px 2px 8px rgba(0,0,0,0.05); }
    .metric-container { background: #f8f9fa; padding: 10px; border-radius: 8px; border-right: 5px solid #007bff; margin: 5px 0; }
    .calendar-day-active { background: #e3f2fd; border: 1px solid #2196f3; border-radius: 4px; padding: 5px; cursor: pointer; min-height: 80px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול מסד נתונים (State Management) ---
if 'db' not in st.session_state:
    st.session_state.db = {
        'fixed_cats': {}, # {id: {name, qty, seats}}
        'games': [],      # [{id, name, date, cats: {name: {qty, seats}}}]
        'sales': []       # [{sale_id, game_id, customer, email, qty, unit_price, total_price, assigned_seats, cat, game_date}]
    }
if 'nav_date' not in st.session_state:
    st.session_state.nav_date = date.today()

db = st.session_state.db

# --- פונקציות לוגיקה ---
def delete_game(game_id):
    st.session_state.db['games'] = [g for g in st.session_state.db['games'] if g['id'] != game_id]
    st.session_state.db['sales'] = [s for s in st.session_state.db['sales'] if s['game_id'] != game_id]

# --- תפריט צד ---
st.sidebar.title("🏟️ ניהול כרטיסים V4")
menu = st.sidebar.radio("ניווט מהיר", ["📅 יומן אינטראקטיבי", "⚽ רשימת משחקים", "⚙️ הגדרות קטגוריות", "📊 דוח מכירות"])

# --- 1. יומן אינטראקטיבי (סעיף 3) ---
if menu == "📅 יומן אינטראקטיבי":
    st.header("📅 יומן משחקים")
    col1, col2 = st.columns([1, 1])
    view_month = col1.selectbox("חודש", range(1, 13), index=date.today().month-1)
    view_year = col2.selectbox("שנה", range(2025, 2027), index=1)
    
    cal = calendar.monthcalendar(view_year, view_month)
    cols = st.columns(7)
    days = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
    for i, d in enumerate(days): cols[i].write(f"**{d}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                curr_date = date(view_year, view_month, day)
                day_games = [g for g in db['games'] if g['date'] == curr_date]
                with cols[i]:
                    st.write(f"**{day}**")
                    for g in day_games:
                        if st.button(f"🏟️ {g['name']}", key=f"btn_{g['id']}"):
                            st.session_state.nav_date = curr_date
                            # מעבר אוטומטי לרשימת המשחקים במיקום הרלוונטי
                            st.info(f"עבור ללשונית 'רשימת משחקים' לצפייה ב-{g['name']}")
                    if st.button("➕", key=f"add_{day}"):
                        st.session_state.nav_date = curr_date
                        st.info(f"עבור ללשונית 'רשימת משחקים' להוספה ל-{day}/{view_month}")

# --- 2. הגדרות קטגוריות (סעיף 3 - עדכון כמות) ---
elif menu == "⚙️ הגדרות קטגוריות":
    st.header("⚙️ קטגוריות קבועות")
    with st.form("new_fixed"):
        c_name = st.text_input("שם קטגוריה")
        c_qty = st.number_input("כמות כרטיסים", min_value=1)
        c_seats = st.text_area("מקומות (מופרדים בפסיק)")
        if st.form_submit_button("שמור קטגוריה"):
            db['fixed_cats'][str(uuid.uuid4())[:8]] = {
                "name": c_name, "qty": c_qty, 
                "seats": [s.strip() for s in c_seats.split(",")] if c_seats else [str(i) for i in range(1, c_qty+1)]
            }
            st.success("נוסף בהצלחה!")
    
    for cid, data in list(db['fixed_cats'].items()):
        with st.expander(f"ערוך: {data['name']}"):
            u_name = st.text_input("שם", data['name'], key=f"un_{cid}")
            u_qty = st.number_input("כמות", value=data['qty'], key=f"uq_{cid}")
            u_seats = st.text_area("מקומות", ",".join(data['seats']), key=f"us_{cid}")
            if st.button("עדכן שינויים", key=f"ub_{cid}"):
                db['fixed_cats'][cid] = {"name": u_name, "qty": u_qty, "seats": [s.strip() for s in u_seats.split(",")]}
                st.rerun()

# --- 3. רשימת משחקים (סעיפים 2, 4, 5) ---
elif menu == "⚽ רשימת משחקים":
    st.header(f"⚽ ניהול משחקים (סה\"כ: {len(db['games'])})") # סעיף 5
    
    with st.expander("➕ צור משחק חדש"):
        with st.form("add_game"):
            g_name = st.text_input("שם המשחק")
            g_date = st.date_input("תאריך", value=st.session_state.nav_date)
            # בחירת קבועות
            sel_fixed = st.multiselect("בחר קטגוריות קבועות", options=list(db['fixed_cats'].keys()), format_func=lambda x: db['fixed_cats'][x]['name'])
            # סעיף 4 - יצירת קטגוריה חדשה בתוך המשחק
            st.subheader("הוסף קטגוריה חדשה למשחק זה")
            new_cat_name = st.text_input("שם קטגוריה חדשה (אופציונלי)")
            new_cat_qty = st.number_input("כמות לחדשה", min_value=0)
            new_cat_seats = st.text_area("מקומות לחדשה")
            save_to_f = st.checkbox("שמור גם כקבועה לעתיד")

            if st.form_submit_button("צור משחק"):
                cats = {db['fixed_cats'][cid]['name']: db['fixed_cats'][cid].copy() for cid in sel_fixed}
                if new_cat_name:
                    s_list = [s.strip() for s in new_cat_seats.split(",")] if new_cat_seats else [str(i) for i in range(1, new_cat_qty+1)]
                    cats[new_cat_name] = {"name": new_cat_name, "qty": new_cat_qty, "seats": s_list}
                    if save_to_f:
                        db['fixed_cats'][str(uuid.uuid4())[:8]] = {"name": new_cat_name, "qty": new_cat_qty, "seats": s_list}
                
                db['games'].append({"id": str(uuid.uuid4())[:8], "name": g_name, "date": g_date, "cats": cats})
                st.rerun()

    # הצגת המשחקים
    for g in db['games']:
        with st.container():
            st.markdown(f"<div class='game-card'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.subheader(f"🏟️ {g['name']} ({g['date']})")
            
            # סעיף 2 - מחיקת משחק
            if col3.button("🗑️ מחק משחק", key=f"del_{g['id']}"):
                delete_game(g['id'])
                st.rerun()
            
            # דאשבורד מלאי (סעיף 6)
            game_sales = [s for s in db['sales'] if s['game_id'] == g['id']]
            cols = st.columns(len(g['cats']) if g['cats'] else 1)
            for idx, (c_name, c_data) in enumerate(g['cats'].items()):
                sold_qty = sum([s['qty'] for s in game_sales if s['cat'] == c_name])
                assigned_qty = sum([len(s['assigned_seats']) for s in game_sales if s['cat'] == c_name])
                with cols[idx]:
                    st.markdown(f"""
                    <div class='metric-container'>
                        <b>{c_name}</b><br>
                        נמכרו: {sold_qty} / {c_data['qty']}<br>
                        <small>מקומות שויכו: {assigned_qty}</small>
                    </div>
                    """, unsafe_allow_html=True)

            t1, t2 = st.tabs(["🛒 מכירה", "🪑 שיוך מקומות"])
            with t1:
                with st.form(f"f_sale_{g['id']}"):
                    c_cat = st.selectbox("קטגוריה", list(g['cats'].keys()))
                    c_cust = st.text_input("לקוח")
                    c_q = st.number_input("כמות", min_value=1)
                    c_p = st.number_input("מחיר ליחידה")
                    # סעיף 4 - בחירת מקומות אופציונלית
                    occupied = [seat for s in game_sales if s['cat'] == c_cat for seat in s['assigned_seats']]
                    available = [s for s in g['cats'][c_cat]['seats'] if s not in occupied]
                    c_seats = st.multiselect("הקצה מקומות (אופציונלי)", available)
                    
                    if st.form_submit_button("בצע מכירה"):
                        if sum([s['qty'] for s in game_sales if s['cat'] == c_cat]) + c_q > g['cats'][c_cat]['qty']:
                            st.warning("שים לב: חריגה מהמלאי המתוכנן!")
                        db['sales'].append({
                            "sale_id": str(uuid.uuid4())[:8], "game_id": g['id'], "customer": c_cust,
                            "cat": c_cat, "qty": c_q, "unit_price": c_p, "total_price": c_p * c_q,
                            "assigned_seats": c_seats, "game_name": g['name'], "game_date": g['date']
                        })
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- 4. דוח מכירות (סעיף 5 - שורה אחת למכירה) ---
elif menu == "📊 דוח מכירות":
    st.header("📊 דוח מכירות מרוכז")
    if db['sales']:
        df = pd.DataFrame(db['sales'])
        # סעיף 5 - שורה אחת למכירה ללא פירוט מקומות בטבלה הראשית
        report_df = df[['customer', 'game_name', 'game_date', 'cat', 'qty', 'unit_price', 'total_price']].copy()
        report_df.columns = ['לקוח', 'משחק', 'תאריך', 'קטגוריה', 'כמות', 'מחיר יחידה', 'סה"כ']
        st.dataframe(report_df, use_container_width=True)
        
        csv = report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ייצוא לאקסל", csv, "tickets_report.csv", "text/csv")
