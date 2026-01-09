import streamlit as st
import pandas as pd

st.set_page_config(page_title="Поиск новых строк (С выбором листов)", layout="wide")

st.title("🆕 Поиск новых строк")
st.markdown("""
Сравнивает два файла и находит записи, которых нет в старом файле.
""")

# --- 1. ЗАГРУЗКА ---
st.sidebar.header("Шаг 1: Загрузка файлов")
file_old = st.sidebar.file_uploader("1. Старый файл (Old)", type=['xlsx'])
file_new = st.sidebar.file_uploader("2. Новый файл (New)", type=['xlsx'])

if file_old and file_new:
    try:
        # Получаем список всех вкладок в обоих файлах
        xls_old = pd.ExcelFile(file_old)
        xls_new = pd.ExcelFile(file_new)
        
        sheets_old = xls_old.sheet_names
        sheets_new = xls_new.sheet_names
        
        # --- 2. ВЫБОР ВКЛАДОК (ЛИСТОВ) ---
        st.header("Шаг 2: Выберите листы таблиц для сравнения")
        col1, col2 = st.columns(2)
        
        with col1:
            sheet_old = st.selectbox(
                "📂 Лист в Старом файле:", 
                sheets_old, 
                help="Выберите таблицу, где содержатся старые данные"
            )
            
        with col2:
            sheet_new = st.selectbox(
                "📂 Лист в Новом файле:", 
                sheets_new, 
                help="Выберите таблицу, где мы ищем новые записи"
            )
        
        # Проверяем, что выбраны листы, и загружаем их для анализа колонок
        if sheet_old and sheet_new:
            # Читаем заголовки из выбранных листов (только первую строку)
            df_sample_old = pd.read_excel(xls_old, sheet_name=sheet_old, nrows=1)
            df_sample_new = pd.read_excel(xls_new, sheet_name=sheet_new, nrows=1)
            
            cols_old = df_sample_old.columns.tolist()
            cols_new = df_sample_new.columns.tolist()
            
            # Находим общие колонки (они пригодятся для выбора ID)
            common_cols = list(set(cols_old) & set(cols_new))
            
            # --- 3. НАСТРОЙКА ПОЛЕЙ ---
            st.header("Шаг 3: Настройка правил сравнения")
            
            # Выбор ключевой колонки (должна быть в ОБЕИХ таблицах)
            key_col = st.selectbox(
                "🔑 Выберите колонку-идентификатор (ID):", 
                common_cols, 
                help="Колонка должна существовать и в старом, и в новом файле (например, ID, Артикул)."
            )
            
            # Настройка колонок для удаления из результата (берем из НОВОГО файла)
            cols_to_drop = st.multiselect(
                "🗑️ Убрать эти колонки из итогового CSV:", 
                cols_new, 
                help="Поля, которые не нужно сохранять в файл с новыми строками."
            )
            
            # --- 4. ЗАПУСК ОБРАБОТКИ ---
            if st.button("🔍 Найти новые строки"):
                st.info("Обрабатываем данные...")
                
                # Читаем данные полностью
                df_old = pd.read_excel(xls_old, sheet_name=sheet_old)
                df_new = pd.read_excel(xls_new, sheet_name=sheet_new)
                
                st.write(f"Загружено строк в старом файле: {len(df_old)}")
                st.write(f"Загружено строк в новом файле: {len(df_new)}")
                
                # Очистка ключевой колонки (приводим к строке и убираем NaN)
                df_old[key_col] = df_old[key_col].astype(str).replace('nan', '')
                df_new[key_col] = df_new[key_col].astype(str).replace('nan', '')
                
                # --- ЛОГИКА ПОИСКА ---
                # Делаем слияние: ищем строки из df_new, которых нет в df_old
                merged = pd.merge(
                    df_new, 
                    df_old[[key_col]], 
                    on=key_col, 
                    how='left', 
                    indicator=True
                )
                
                # Отфильтровываем только новые (left_only)
                new_rows_df = merged[merged['_merge'] == 'left_only']
                
                # Удаляем служебную колонку
                new_rows_df = new_rows_df.drop(columns=['_merge'])
                
                # Удаляем ненужные колонки, если выбраны
                if cols_to_drop:
                    new_rows_df = new_rows_df.drop(columns=[c for c in cols_to_drop if c in new_rows_df.columns])
                
                # --- 5. РЕЗУЛЬТАТ ---
                st.header("Результат")
                count = len(new_rows_df)
                
                if count > 0:
                    st.success(f"✅ Найдено новых строк: **{count}**")
                    
                    st.dataframe(new_rows_df, use_container_width=True)
                    
                    csv = new_rows_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Скачать результат в CSV",
                        data=csv,
                        file_name='new_rows_found.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("⚠️ Новых строк не обнаружено. Все ID из нового файла уже присутствуют в старом.")

    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.error(str(e))
else:
    st.info("Пожалуйста, загрузите оба файла, чтобы начать.")
