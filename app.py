import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# הגדרות תצוגה RTL ועיצוב מתקדם
st.set_page_config(page_title="מערכת ניהול כרטיסים PRO", layout="wide")
st.markdown("""
    <style>
    .main { text-align: right; direction: rtl; }
    div[data-testid="stBlock"] { direction: rtl; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול מסד נתונים בזיכרון ---
if 'db' not in st.session_state:
    st.session_state.db = {
        'fixed_cats': {}, # {id: {name, qty, seats}}
        'games': [],      # [{id, name, date, cats: {name: {qty, seats}}}]
        'sales': []       # [{id, game_id, customer, email, qty, seats, cat, price, total, game_date, created_at}]
    }

db = st.session_state.db

# --- פונקציות עזר ---
def get_game_sales(game_id):
    return [s for s in db['sales'] if s['game_id'] == game_id]

# --- תפריט צד מעוצב ---
st.sidebar.title("🎫 ניהול מערך כרטיסים")
menu = st.sidebar.selectbox("עבור אל:", ["📅 יומן משחקים", "⚙️ ניהול קטגוריות קבועות", "📊 דוח מכירות מפורט"])

# --- 1. ניהול קטגוריות קבועות (תיקון סעיף 4, 7) ---
if menu == "⚙️ ניהול קטגוריות קבועות":
    st.header("⚙️ הגדרת קטגוריות קבועות")
    
    with st.expander("➕ הוסף קטגוריה חדשה לרשימה"):
        with st.form("add_fixed"):
            name = st.text_input("שם הקטגוריה")
            qty = st.number_input("כמות כרטיסים ברירת מחדל", min_value=1)
            seats = st.text_area("רשימת מקומות (מופרדים בפסיק)")
            if st.form_submit_button("שמור במערכת"):
                cat_id = str(uuid.uuid4())[:8]
                seat_list = [s.strip() for s in seats.split(",")] if seats else [str(i) for i in range(1, qty+1)]
                db['fixed_cats'][cat_id] = {"name": name, "qty": len(seat_list), "seats": seat_list}
                st.success("הקטגוריה נוספה!")

    if db['fixed_cats']:
        st.subheader("רשימת קטגוריות קיימות (ניתן לערוך)")
        for cid, data in list(db['fixed_cats'].items()):
            with st.expander(f"🛠️ {data['name']} ({data['qty']} מקומות)"):
                new_name = st.text_input("ערוך שם", data['name'], key=f"edit_n_{cid}")
                new_seats = st.text_area("ערוך מקומות", ",".join(data['seats']), key=f"edit_s_{cid}")
                col1, col2 = st.columns(2)
                if col1.button("עדכן שינויים", key=f"upd_{cid}"):
                    db['fixed_cats'][cid] = {"name": new_name, "qty": len([s.strip() for s in new_seats.split(",")]), "seats": [s.strip() for s in new_seats.split(",")]}
                    st.rerun()
                if col2.button("מחק קטגוריה", key=f"del_{cid}"):
                    del db['fixed_cats'][cid]
                    st.rerun()

# --- 2. יומן משחקים (תיקון סעיף 1, 2, 3, 5) ---
elif menu == "📅 יומן משחקים":
    st.header("📅 יומן ומעקב משחקים")
    
    col_cal, col_info = st.columns([1, 3])
    
    with col_cal:
        selected_date = st.date_input("בחר תאריך לצפייה/הוספה")
        if st.button("➕ הוסף משחק לתאריך זה"):
            st.session_state.show_add_game = True

    # הוספת משחק (סעיף 2 - קבועות וחדשות)
    if st.session_state.get('show_add_game'):
        with st.form("new_game_form"):
            g_name = st.text_input("שם המשחק")
            st.write("בחר קטגוריות למשחק זה:")
            
            # בחירת קטגוריות קבועות
            selected_fixed = st.multiselect("קטגוריות קבועות להוספה", 
                                            options=list(db['fixed_cats'].keys()),
                                            format_func=lambda x: db['fixed_cats'][x]['name'])
            
            st.info("רוצה להוסיף קטגוריה חד פעמית? מלא כאן:")
            extra_cat_name = st.text_input("שם קטגוריה חדשה")
            extra_cat_seats = st.text_area("מקומות (מופרדים בפסיק)")
            save_to_fixed = st.checkbox("שמור גם כקטגוריה קבועה לעתיד")

            if st.form_submit_button("צור משחק"):
                game_cats = {}
                # הוספת קבועות
                for cid in selected_fixed:
                    f_cat = db['fixed_cats'][cid]
                    game_cats[f_cat['name']] = {"qty": f_cat['qty'], "seats": list(f_cat['seats'])}
                
                # הוספת חד פעמית
                if extra_cat_name:
                    s_list = [s.strip() for s in extra_cat_seats.split(",")]
                    game_cats[extra_cat_name] = {"qty": len(s_list), "seats": s_list}
                    if save_to_fixed:
                        db['fixed_cats'][str(uuid.uuid4())[:8]] = {"name": extra_cat_name, "qty": len(s_list), "seats": s_list}
                
                db['games'].append({"id": str(uuid.uuid4())[:8], "name": g_name, "date": selected_date, "cats": game_cats})
                st.session_state.show_add_game = False
                st.rerun()

    # הצגת משחקים לתאריך הנבחר
    day_games = [g for g in db['games'] if g['date'] == selected_date]
    
    if not day_games:
        st.info("אין משחקים רשומים לתאריך זה.")
    else:
        for game in day_games:
            with st.container():
                st.markdown(f"### 🏟️ {game['name']}")
                
                # תצוגת דאשבורד משחק (סעיף 5)
                cols = st.columns(len(game['cats']) if game['cats'] else 1)
                for idx, (c_name, c_data) in enumerate(game['cats'].items()):
                    sold_count = len([s for s in get_game_sales(game['id']) if s['cat'] == c_name])
                    with cols[idx]:
                        st.metric(c_name, f"{sold_count}/{c_data['qty']} נמכרו")
                
                t1, t2, t3 = st.tabs(["🛒 ביצוע מכירה", "🪑 מפת מקומות וסטטוס", "✏️ עריכת קטגוריות למשחק"])
                
                with t1: # (סעיף 6 - כמות ומקומות)
                    with st.form(f"sale_{game['id']}"):
                        cat_sel = st.selectbox("בחר קטגוריה", list(game['cats'].keys()))
                        c_name = st.text_input("שם לקוח")
                        c_qty = st.number_input("כמות כרטיסים", min_value=1, step=1)
                        
                        # סינון מקומות פנויים
                        occupied = [s['seat'] for s in get_game_sales(game['id']) if s['cat'] == cat_sel]
                        available = [s for s in game['cats'][cat_sel]['seats'] if s not in occupied]
                        
                        sel_seats = st.multiselect(f"בחר {c_qty} מקומות", available)
                        
                        col_p1, col_p2 = st.columns(2)
                        u_price = col_p1.number_input("מחיר לכרטיס", min_value=0)
                        u_cost = col_p2.number_input("עלות לכרטיס (שלך)", min_value=0)
                        
                        if st.form_submit_button("אשר מכירה"):
                            if len(sel_seats) != c_qty:
                                st.error(f"עליך לבחור בדיוק {c_qty} מקומות!")
                            else:
                                for s_code in sel_seats:
                                    db['sales'].append({
                                        "game_id": game['id'], "customer": c_name, "cat": cat_sel,
                                        "qty": 1, "seat": s_code, "price": u_price, "cost": u_cost,
                                        "total": u_price, "game_name": game['name'], "game_date": game['date'],
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                    })
                                st.success("המכירה בוצעה!")
                                st.rerun()

                with t2: # סטטוס מקומות מלא (סעיף 5)
                    cat_view = st.selectbox("ראה מקומות עבור:", list(game['cats'].keys()), key=f"view_{game['id']}")
                    seat_map = []
                    for s in game['cats'][cat_view]['seats']:
                        owner = next((sl['customer'] for sl in get_game_sales(game['id']) if sl['cat'] == cat_view and sl['seat'] == s), "✅ פנוי")
                        seat_map.append({"מקום": s, "סטטוס/שם לקוח": owner})
                    st.table(pd.DataFrame(seat_map))

                with t3: # עריכת קטגוריות למשחק ספציפי (סעיף 3)
                    st.warning("שינויים כאן ישפיעו רק על המשחק הזה!")
                    for c_name, c_data in game['cats'].items():
                        new_s = st.text_area(f"ערוך מקומות ל-{c_name}", ",".join(c_data['seats']), key=f"loc_edit_{game['id']}_{c_name}")
                        if st.button(f"עדכן {c_name} למשחק זה"):
                            game['cats'][c_name]['seats'] = [x.strip() for x in new_s.split(",")]
                            game['cats'][c_name]['qty'] = len(game['cats'][c_name]['seats'])
                            st.success("עודכן!")

# --- 3. דוח מכירות (תיקון סעיף 8) ---
elif menu == "📊 דוח מכירות מפורט":
    st.header("📊 דוח מכירות וביצועים")
    if db['sales']:
        df = pd.DataFrame(db['sales'])
        # סידור עמודות לפי בקשה
        cols_order = ['customer', 'cat', 'seat', 'price', 'total', 'game_name', 'game_date', 'created_at']
        df = df[cols_order]
        df.columns = ['לקוח', 'קטגוריה', 'מקום', 'מחיר ליחידה', 'סה"כ שולם', 'משחק', 'תאריך משחק', 'תאריך מכירה']
        
        st.dataframe(df.sort_values(by='תאריך מכירה', ascending=False), use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ייצוא לאקסל (CSV)", csv, "sales_report.csv", "text/csv")
    else:
        st.info("אין נתוני מכירות להצגה.")
