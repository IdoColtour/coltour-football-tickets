import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
import uuid

# --- הגדרות עיצוב ו-RTL ---
st.set_page_config(page_title="Ticket Master Pro", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stMetric { background: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 12px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .calendar-card { border: 1px solid #ddd; padding: 10px; border-radius: 8px; background: #f9f9f9; min-height: 100px; }
    .game-badge { background: #007bff; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול מסד הנתונים (מקומי עם הכנה לגוגל שיטס) ---
if 'db' not in st.session_state:
    st.session_state.db = {
        'fixed_cats': {}, # {id: {name, qty, seats}}
        'games': [],      # [{id, name, date, cats: {name: {qty, seats}}}]
        'sales': []       # [{sale_id, game_id, customer, email, qty, unit_price, total_price, assigned_seats, cat, game_date}]
    }

db = st.session_state.db

# --- פונקציות לוגיקה ---
def get_game_stats(game_id):
    game_sales = [s for s in db['sales'] if s['game_id'] == game_id]
    stats = {}
    for s in game_sales:
        stats[s['cat']] = stats.get(s['cat'], {'sold': 0, 'assigned': 0})
        stats[s['cat']]['sold'] += s['qty']
        stats[s['cat']]['assigned'] += len(s['assigned_seats'])
    return stats

# --- תפריט ראשי ---
st.sidebar.title("🎫 מערכת ניהול כרטיסים")
menu = st.sidebar.selectbox("תפריט", ["📅 יומן ויזואלי", "🏟️ ניהול משחקים", "⚙️ הגדרות קטגוריות", "📊 דוח מכירות"])

# --- 1. יומן ויזואלי גדול (תיקון סעיף 2) ---
if menu == "📅 יומן ויזואלי":
    st.header("📅 יומן משחקים חודשי")
    
    today = date.today()
    col_y, col_m = st.columns(2)
    curr_year = col_y.selectbox("שנה", range(today.year, today.year+2), index=0)
    curr_month = col_m.selectbox("חודש", range(1, 13), index=today.month-1)
    
    cal = calendar.monthcalendar(curr_year, curr_month)
    month_name = calendar.month_name[curr_month]
    
    # יצירת גריד של ימים
    days_header = ["ב'", "ג'", "ד'", "ה'", "ו'", "ש'", "א'"]
    cols = st.columns(7)
    for i, day in enumerate(days_header):
        cols[i].markdown(f"**{day}**")
    
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                d_date = date(curr_year, curr_month, day)
                day_games = [g for g in db['games'] if g['date'] == d_date]
                with cols[i]:
                    st.markdown(f"**{day}**")
                    for g in day_games:
                        st.markdown(f"<div class='game-badge'>{g['name']}</div>", unsafe_allow_html=True)
                    if st.button("+", key=f"add_{day}"):
                        st.session_state.target_date = d_date
                        st.info(f"עבור ללשונית 'ניהול משחקים' להוספת משחק ל-{d_date}")

# --- 2. הגדרות קטגוריות (תיקון סעיף 3) ---
elif menu == "⚙️ הגדרות קטגוריות":
    st.header("⚙️ ניהול קטגוריות קבועות")
    with st.expander("➕ הוסף קטגוריה חדשה"):
        with st.form("new_cat"):
            name = st.text_input("שם הקטגוריה")
            qty = st.number_input("כמות כרטיסים", min_value=1)
            seats = st.text_area("שמות מקומות (אופציונלי, הפרד בפסיק)")
            if st.form_submit_button("שמור"):
                cid = str(uuid.uuid4())[:8]
                s_list = [s.strip() for s in seats.split(",")] if seats else []
                db['fixed_cats'][cid] = {"name": name, "qty": qty, "seats": s_list}
                st.success("נשמר!")

    for cid, data in list(db['fixed_cats'].items()):
        with st.expander(f"🛠️ {data['name']}"):
            # תיקון סעיף 3 - שינוי כמות
            u_name = st.text_input("שם", data['name'], key=f"n_{cid}")
            u_qty = st.number_input("כמות כרטיסים", value=data['qty'], key=f"q_{cid}")
            u_seats = st.text_area("מקומות", ",".join(data['seats']), key=f"s_{cid}")
            if st.button("עדכן", key=f"upd_{cid}"):
                db['fixed_cats'][cid] = {"name": u_name, "qty": u_qty, "seats": [s.strip() for s in u_seats.split(",")] if u_seats else []}
                st.rerun()

# --- 3. ניהול משחקים ומכירות (תיקון סעיף 4, 6) ---
elif menu == "🏟️ ניהול משחקים":
    st.header("🏟️ ניהול ומכירת כרטיסים")
    
    # הוספת משחק
    with st.expander("➕ צור משחק חדש"):
        g_name = st.text_input("שם המשחק")
        g_date = st.date_input("תאריך", value=st.session_state.get('target_date', date.today()))
        selected_fixed = st.multiselect("בחר קטגוריות קבועות", options=list(db['fixed_cats'].keys()), format_func=lambda x: db['fixed_cats'][x]['name'])
        if st.button("צור משחק"):
            cats = {}
            for cid in selected_fixed:
                f = db['fixed_cats'][cid]
                cats[f['name']] = {"qty": f['qty'], "seats": list(f['seats'])}
            db['games'].append({"id": str(uuid.uuid4())[:8], "name": g_name, "date": g_date, "cats": cats})
            st.success("משחק נוצר!")

    for g in db['games']:
        with st.expander(f"⚽ {g['name']} | {g['date']}"):
            stats = get_game_stats(g['id'])
            
            # תצוגת סטטיסטיקה (סעיף 6)
            st.subheader("מצב מלאי")
            cols = st.columns(len(g['cats']) if g['cats'] else 1)
            for i, (c_name, c_data) in enumerate(g['cats'].items()):
                c_stat = stats.get(c_name, {'sold': 0, 'assigned': 0})
                with cols[i]:
                    st.markdown(f"""
                    <div class='stMetric'>
                        <b>{c_name}</b><br>
                        <span style='font-size: 20px;'>נמכרו: {c_stat['sold']} / {c_data['qty']}</span><br>
                        <small>מקומות שחולקו: {c_stat['assigned']}</small>
                    </div>
                    """, unsafe_allow_html=True)

            t1, t2 = st.tabs(["🛒 מכירה חדשה", "🪑 ניהול מקומות"])
            
            with t1:
                with st.form(f"sale_{g['id']}"):
                    cat_sel = st.selectbox("בחר קטגוריה", list(g['cats'].keys()))
                    c_name = st.text_input("שם לקוח")
                    c_qty = st.number_input("כמות כרטיסים", min_value=1)
                    u_price = st.number_input("מחיר לכרטיס")
                    
                    # סעיף 4 - מקומות הם אופציונליים
                    occupied = [seat for s in db['sales'] if s['game_id'] == g['id'] and s['cat'] == cat_sel for seat in s['assigned_seats']]
                    available = [s for s in g['cats'][cat_sel]['seats'] if s not in occupied]
                    sel_seats = st.multiselect("הקצה מקומות עכשיו (אופציונלי)", available)
                    
                    if st.form_submit_button("בצע מכירה"):
                        # אזהרת מלאי (סעיף 6)
                        current_sold = stats.get(cat_sel, {'sold': 0})['sold']
                        if current_sold + c_qty > g['cats'][cat_sel]['qty']:
                            st.warning("שים לב: המכירה חורגת מהמלאי המוגדר!")
                        
                        db['sales'].append({
                            "sale_id": str(uuid.uuid4())[:8], "game_id": g['id'], "customer": c_name,
                            "cat": cat_sel, "qty": c_qty, "unit_price": u_price, "total_price": u_price * c_qty,
                            "assigned_seats": sel_seats, "game_date": g['date'], "game_name": g['name']
                        })
                        st.success("מכירה נרשמה!")
                        st.rerun()

            with t2:
                # ניהול והקצאת מקומות למכירות קיימות
                st.subheader("הקצאת מקומות למכירות")
                relevant_sales = [s for s in db['sales'] if s['game_id'] == g['id']]
                for s in relevant_sales:
                    if len(s['assigned_seats']) < s['qty']:
                        st.write(f"⚠️ {s['customer']} - חסרים {s['qty'] - len(s['assigned_seats'])} מקומות")
                        # כאן אפשר להוסיף כפתור להקצאה מהירה

# --- 4. דוח מכירות (תיקון סעיף 5) ---
elif menu == "📊 דוח מכירות":
    st.header("📊 דוח מכירות")
    if db['sales']:
        # סעיף 5 - שורה אחת לכל מכירה, ללא פירוט מקומות (למען הסדר)
        df = pd.DataFrame(db['sales'])
        display_df = df[['customer', 'game_name', 'game_date', 'cat', 'qty', 'unit_price', 'total_price']].copy()
        display_df.columns = ['לקוח', 'משחק', 'תאריך משחק', 'קטגוריה', 'כמות', 'מחיר יחידה', 'סה"כ']
        
        st.dataframe(display_df, use_container_width=True)
        
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ייצוא לאקסל", csv, "sales.csv", "text/csv")
