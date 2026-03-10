import streamlit as st
import pandas as pd
from datetime import datetime

# הגדרות עיצוב בסיסיות
st.set_page_config(page_title="ניהול כרטיסי כדורגל", layout="wide")

# פונקציות עזר לאחסון נתונים (כרגע בזיכרון האפליקציה)
if 'fixed_categories' not in st.session_state:
    st.session_state.fixed_categories = {}
if 'games' not in st.session_state:
    st.session_state.games = []
if 'sales' not in st.session_state:
    st.session_state.sales = []

# --- תפריט צד ---
st.sidebar.title("⚽ מערכת כרטיסים")
menu = st.sidebar.radio("ניווט", ["יומן משחקים", "קטגוריות קבועות", "דו''ח מכירות"])

# --- 1. קטגוריות קבועות ---
if menu == "קטגוריות קבועות":
    st.header("📋 ניהול קטגוריות קבועות")
    with st.form("new_fixed"):
        col1, col2 = st.columns(2)
        name = col1.text_input("שם הקטגוריה (למשל: VIP, יציע מזרחי)")
        qty = col2.number_input("כמות כרטיסים", min_value=1, value=10)
        seats = st.text_area("רשימת מקומות (הפרד בפסיק , ) - אופציונלי")
        if st.form_submit_button("שמור קטגוריה"):
            seat_list = [s.strip() for s in seats.split(",")] if seats else [str(i) for i in range(1, qty+1)]
            st.session_state.fixed_categories[name] = {"qty": qty, "seats": seat_list}
            st.success("נשמר!")
    
    if st.session_state.fixed_categories:
        st.write("קטגוריות קיימות:")
        st.table(pd.DataFrame([{"שם": k, "כמות": v['qty']} for k, v in st.session_state.fixed_categories.items()]))

# --- 2. יומן משחקים (עמוד ראשי) ---
elif menu == "יומן משחקים":
    st.header("📅 יומן משחקים")
    
    # הוספת משחק
    with st.expander("➕ הוסף משחק חדש ליומן"):
        g_name = st.text_input("שם המשחק")
        g_date = st.date_input("תאריך המשחק")
        selected_cats = st.multiselect("בחר קטגוריות למשחק", list(st.session_state.fixed_categories.keys()))
        if st.button("צור משחק"):
            new_game = {
                "id": len(st.session_state.games),
                "name": g_name,
                "date": g_date,
                "categories": {cat: st.session_state.fixed_categories[cat].copy() for cat in selected_cats}
            }
            st.session_state.games.append(new_game)
            st.success("המשחק נוסף ליומן!")

    # תצוגת המשחקים ביומן
    if st.session_state.games:
        for i, game in enumerate(st.session_state.games):
            with st.expander(f"🏟️ {game['name']} | {game['date']}"):
                tab1, tab2 = st.tabs(["מכירה חדשה", "סטטוס מלאי ומקומות"])
                
                with tab1:
                    st.subheader("רישום מכירה")
                    cat_choice = st.selectbox(f"בחר קטגוריה - {game['name']}", list(game['categories'].keys()), key=f"sel_{i}")
                    
                    # לוגיקת מקומות
                    all_seats = game['categories'][cat_choice]['seats']
                    sold_seats = [s['seat'] for s in st.session_state.sales if s['game_id'] == i and s['category'] == cat_choice]
                    available_seats = [s for s in all_seats if s not in sold_seats]
                    
                    with st.form(f"sale_form_{i}"):
                        c_name = st.text_input("שם לקוח")
                        c_email = st.text_input("מייל")
                        c_price = st.number_input("מחיר ששולם", min_value=0)
                        c_cost = st.number_input("מחיר עלות", min_value=0)
                        chosen_seat = st.selectbox("בחר מקום פנוי", available_seats)
                        
                        if st.form_submit_button("בצע מכירה"):
                            st.session_state.sales.append({
                                "game_id": i,
                                "customer": c_name,
                                "email": c_email,
                                "category": cat_choice,
                                "price": c_price,
                                "cost": c_cost,
                                "seat": chosen_seat
                            })
                            st.success("המכירה נרשמה!")
                            st.rerun()

                with tab2:
                    st.subheader("תמונת מצב")
                    # טבלת מקומות מלאה
                    seat_status = []
                    for s in all_seats:
                        occupant = next((sale['customer'] for sale in st.session_state.sales if sale['game_id'] == i and sale['category'] == cat_choice and sale['seat'] == s), "פנוי")
                        seat_status.append({"מקום": s, "סטטוס/לקוח": occupant})
                    st.table(pd.DataFrame(seat_status))

# --- 3. דו"חות וייצוא ---
elif menu == "דו''ח מכירות":
    st.header("📊 ריכוז מכירות")
    if st.session_state.sales:
        df_sales = pd.DataFrame(st.session_state.sales)
        st.dataframe(df_sales)
        
        # ייצוא לאקסל
        csv = df_sales.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 הורד את כל הנתונים לאקסל (CSV)", data=csv, file_name="sales_report.csv", mime="text/csv")
    else:
        st.info("עדיין אין מכירות במערכת.")
