import streamlit as st
import pandas as pd

st.set_page_config(page_title="Поиск новых строк с фильтрацией", layout="wide")

st.title("🆕 Поиск новых строк с фильтрацией")
st.markdown("""
Сравнивает два файла, находит новые записи и позволяет отфильтровать их по значению в любой колонке.
""")

# --- 1. ЗАГРУЗКА ---
st.sidebar.header("Шаг 1: Загрузка файлов")
file_old = st.sidebar.file_uploader("1. Старый файл (Old)", type=['xlsx'])
file_new = st.sidebar.file_uploader("2. Новый файл (New)", type=['xlsx'])

if file_old and file_new:
    try:
        xls_old = pd.ExcelFile(file_old)
        xls_new = pd.ExcelFile(file_new)
        
        sheets_old = xls_old.sheet_names
        sheets_new = xls_new.sheet_names
        
        # --- 2. ВЫБОР ВКЛАДОК ---
        st.header("Шаг 2: Выберите листы таблиц для сравнения")
        col1, col2 = st.columns(2)
        
        with col1:
            sheet_old = st.selectbox("📂 Лист в Старом файле:", sheets_old)
        with col2:
            sheet_new = st.selectbox("📂 Лист в Новом файле:", sheets_new)
            
        if sheet_old and sheet_new:
            # Загружаем только заголовки для анализа колонок
            df_sample_old = pd.read_excel(xls_old, sheet_name=sheet_old, nrows=1)
            df_sample_new = pd.read_excel(xls_new, sheet_name=sheet_new, nrows=1)
            
            cols_old = df_sample_old.columns.tolist()
            cols_new = df_sample_new.columns.tolist()
            
            # Находим общие колонки для выбора ключа
            common_cols = list(set(cols_old) & set(cols_new))
            common_cols.sort()
            
            # --- 3. НАСТРОЙКИ КЛЮЧА ---
            st.header("Шаг 3: Настройка идентификатора")
            key_col = st.selectbox(
                "🔑 Выберите колонку-идентификатор (ID):", 
                common_cols, 
                help="Колонка должна существовать в обоих файлах."
            )
            
            # --- 4. НОВАЯ ФУНКЦИЯ: ФИЛЬТР ПО ЗНАЧЕНИЯМ ---
            st.header("Шаг 4: Фильтрация по значениям (опционально)")
            use_filter = st.checkbox("🔎 Включить фильтр по значениям в колонке", value=False, help="Оставить только строки с конкретными значениями")
            
            filter_col = None
            filter_values = []
            
            if use_filter:
                # Фильтр применяем к колонкам НОВОГО файла (так как ищем в нем)
                filter_col = st.selectbox("Выберите колонку для фильтрации:", cols_new)
                
                if filter_col:
                    # Подгружаем уникальные значения для выпадающего списка
                    # Читаем весь файл, чтобы точно получить все варианты
                    with st.spinner('Загружаем список значений для фильтра...'):
                        df_for_filter = pd.read_excel(xls_new, sheet_name=sheet_new)
                        
                    # Очищаем значения от пустых и приводим к строке для корректного отображения
                    unique_vals = df_for_filter[filter_col].dropna().unique()
                    unique_vals = [str(x) for x in unique_vals]
                    unique_vals.sort()
                    
                    # Ограничиваем вывод, если значений очень много (более 100), чтобы не зависло
                    if len(unique_vals) > 100:
                        st.warning(f"В колонке более 100 уникальных значений. Показаны первые 100.")
                        display_vals = unique_vals[:100]
                    else:
                        display_vals = unique_vals
                    
                    filter_values = st.multiselect(
                        f"Выберите значения '{filter_col}', которые нужно оставить:", 
                        display_vals
                    )
                    
                    if not filter_values:
                        st.warning("Если не выбрать ни одного значения, фильтр не сработает.")

            # --- 5. УДАЛЕНИЕ КОЛОНОК ---
            st.header("Шаг 5: Настройка финального файла")
            cols_to_drop = st.multiselect(
                "🗑️ Убрать эти колонки из итогового CSV:", 
                cols_new, 
                help="Эти поля будут удалены перед сохранением."
            )
            
            # --- 6. ЗАПУСК ---
            if st.button("🔍 Найти и отфильтровать строки"):
                st.info("Выполняем расчеты...")
                
                # Читаем данные полностью
                df_old = pd.read_excel(xls_old, sheet_name=sheet_old)
                df_new = pd.read_excel(xls_new, sheet_name=sheet_new)
                
                st.write(f"Строк в старом файле: {len(df_old)}")
                st.write(f"Строк в новом файле: {len(df_new)}")
                
                # Подготовка ID
                df_old[key_col] = df_old[key_col].astype(str).replace('nan', '')
                df_new[key_col] = df_new[key_col].astype(str).replace('nan', '')
                
                # 1. Слияние (поиск новых)
                merged = pd.merge(
                    df_new, 
                    df_old[[key_col]], 
                    on=key_col, 
                    how='left', 
                    indicator=True
                )
                new_rows_df = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
                
                intermediate_count = len(new_rows_df)
                
                # 2. Применение пользовательского фильтра (по значениям)
                if use_filter and filter_col and filter_values:
                    # Преобразуем значения фильтра к строкам для точного совпадения
                    filter_values_str = [str(v) for v in filter_values]
                    
                    # Приводим колонку в датафрейме к строке
                    new_rows_df[filter_col] = new_rows_df[filter_col].astype(str)
                    
                    # Фильтруем
                    new_rows_df = new_rows_df[new_rows_df[filter_col].isin(filter_values_str)]
                    
                    st.info(f"🔎 После фильтра по '{filter_col}': осталось строк {len(new_rows_df)} (из {intermediate_count} найденных).")
                elif use_filter:
                    st.warning("Фильтр включен, но не выбраны значения. Выводятся все найденные строки.")
                
                # 3. Удаление лишних колонок
                if cols_to_drop:
                    cols_to_drop_clean = [c for c in cols_to_drop if c in new_rows_df.columns]
                    new_rows_df = new_rows_df.drop(columns=cols_to_drop_clean)
                
                # --- 7. РЕЗУЛЬТАТ ---
                st.header("Результат")
                count = len(new_rows_df)
                
                if count > 0:
                    st.success(f"✅ Итого строк для выгрузки: **{count}**")
                    
                    st.dataframe(new_rows_df, use_container_width=True)
                    
                    csv = new_rows_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 Скачать результат (CSV)",
                        data=csv,
                        file_name='filtered_new_rows.csv',
                        mime='text/csv'
                    )
                else:
                    st.warning("⚠️ Нет данных, соответствующих критериям.")

    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.error(str(e))
else:
    st.info("Пожалуйста, загрузите оба файла.")
