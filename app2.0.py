import streamlit as st
import pandas as pd
import datetime

# Настройка страницы
st.set_page_config(page_title="Сравнение Excel (Сортировка и Даты)", layout="wide")

st.title("📊 Сравнение Excel v2.0")
st.markdown("""
**Исправления:**
1.  **Сортировка:** Выберите ключевую колонку (например, ID, Артикул), чтобы файлы выстроились в одном порядке. Это необходимо для корректного поиска новых строк.
2.  **Даты:** Опция игнорировать время при сравнении дат.
""")

# --- 1. ПРИНИМАЕМ ДВА ФАЙЛА ---
st.sidebar.header("Загрузка файлов")
file1 = st.sidebar.file_uploader("1. Файл за День 1 (Старый)", type=['xlsx'])
file2 = st.sidebar.file_uploader("2. Файл за День 2 (Новый)", type=['xlsx'])

if file1 and file2:
    try:
        xls1 = pd.ExcelFile(file1)
        xls2 = pd.ExcelFile(file2)
        
        sheets1 = xls1.sheet_names
        sheets2 = xls2.sheet_names
        
        common_sheets = list(set(sheets1) & set(sheets2))
        common_sheets.sort()
        
        if not common_sheets:
            st.error("Нет общих вкладок для сравнения!")
        else:
            # --- 2. ВЫБОР ВКЛАДОК ---
            selected_sheets = st.multiselect("Выберите вкладки:", common_sheets, default=common_sheets)
            
            ignored_cols_map = {}
            sort_col_map = {} # Карта для колонок сортировки
            
            if selected_sheets:
                st.subheader("Настройки сравнения")
                
                # Для каждой вкладки задаем настройки
                for sheet in selected_sheets:
                    with st.expander(f"Настройки для вкладки: '{sheet}'"):
                        df_preview = pd.read_excel(xls1, sheet_name=sheet, nrows=1)
                        columns = df_preview.columns.tolist()
                        
                        # ВЫБОР КЛЮЧЕВОЙ КОЛОНКИ ДЛЯ СОРТИРОВКИ
                        sort_key = st.selectbox(
                            f"🔑 Колонка для сортировки (Ключ):", 
                            columns, 
                            key=f"sort_{sheet}",
                            help="Обычно это 'ID', 'Номер', 'Артикул'. Файлы будут отсортированы по этой колонке перед сравнением."
                        )
                        sort_col_map[sheet] = sort_key
                        
                        # ВЫБОР ИГНОРИРУЕМЫХ КОЛОНОК
                        ignored = st.multiselect(
                            f"❌ Игнорировать столбцы:", 
                            columns, 
                            key=f"ignore_{sheet}"
                        )
                        ignored_cols_map[sheet] = ignored
            
            if st.button("🚀 Запустить сравнение"):
                if not selected_sheets:
                    st.warning("Выберите вкладки.")
                else:
                    all_results = {}
                    progress_bar = st.progress(0)
                    
                    # Глобальная настройка дат
                    ignore_time_in_dates = st.checkbox("Игнорировать время в полях с датой", value=True)
                    
                    # --- 4. ЛОГИКА СРАВНЕНИЯ ---
                    for i, sheet in enumerate(selected_sheets):
                        df1 = pd.read_excel(xls1, sheet_name=sheet).fillna('')
                        df2 = pd.read_excel(xls2, sheet_name=sheet).fillna('')
                        
                        # --- ВАЖНО: СОРТИРОВКА ---
                        # Сортируем оба датафрейма по выбранной колонке, чтобы выровнять строки
                        sort_col = sort_col_map[sheet]
                        try:
                            df1 = df1.sort_values(by=sort_col).reset_index(drop=True)
                            df2 = df2.sort_values(by=sort_col).reset_index(drop=True)
                        except Exception as e:
                            st.warning(f"Не удалось отсортировать вкладку '{sheet}' по колонке '{sort_col}'. Сравнение может быть неточным. Ошибка: {e}")

                        # Получаем список колонок для игнорирования
                        current_ignored = ignored_cols_map.get(sheet, [])
                        cols_to_compare = [c for c in df1.columns if c not in current_ignored]
                        
                        # Определяем, какие колонки похожи на даты, чтобы обрабатывать их отдельно
                        date_columns = []
                        if ignore_time_in_dates:
                            for col in df1.columns:
                                if pd.api.types.is_datetime64_any_dtype(df1[col]):
                                    date_columns.append(col)
                        
                        max_rows = max(len(df1), len(df2))
                        results = []
                        
                        for row_idx in range(max_rows):
                            row_data = {}
                            status = ""
                            
                            # Логика НОВОЙ строки (если во втором файле строк больше)
                            if row_idx >= len(df1):
                                status = "🟢 Добавлено"
                                for col in df2.columns:
                                    row_data[f"{col}_Day2"] = df2.at[row_idx, col]
                                for col in df1.columns:
                                    row_data[f"{col}_Day1"] = ""
                            
                            # Логика УДАЛЕННОЙ строки (пропускаем)
                            elif row_idx >= len(df2):
                                continue 
                            
                            # Логика ИЗМЕНЕНИЯ
                            else:
                                is_different = False
                                
                                for col in df1.columns:
                                    val1 = df1.at[row_idx, col]
                                    val2 = df2.at[row_idx, col] if col in df2.columns else ""
                                    
                                    row_data[f"{col}_Day1"] = val1
                                    row_data[f"{col}_Day2"] = val2
                                    
                                    # Логика сравнения с учетом дат
                                    if col in cols_to_compare:
                                        diff = False
                                        
                                        if ignore_time_in_dates and (col in date_columns or pd.api.types.is_datetime64_any_dtype(df2[col])):
                                            # Пытаемся преобразовать к дате и сравнить только дату
                                            try:
                                                d1 = pd.to_datetime(val1, errors='coerce')
                                                d2 = pd.to_datetime(val2, errors='coerce')
                                                
                                                if pd.notna(d1) and pd.notna(d2):
                                                    # Сравниваем .date() (без времени)
                                                    if d1.date() != d2.date():
                                                        diff = True
                                                else:
                                                    # Если одна из них не дата, сравниваем как строки
                                                    if str(val1) != str(val2):
                                                        diff = True
                                            except:
                                                # Ошибка парсинга даты - сравниваем как строки
                                                if str(val1) != str(val2):
                                                    diff = True
                                        else:
                                            # Обычное сравнение строк/чисел
                                            if str(val1) != str(val2):
                                                diff = True
                                        
                                        if diff:
                                            is_different = True
                                
                                if is_different:
                                    status = "🟡 Изменено"
                                else:
                                    status = "⚪ Без изменений"
                            
                            # Фильтр
                            if status in ["🟢 Добавлено", "🟡 Изменено"]:
                                row_data['Status'] = status
                                results.append(row_data)

                        if results:
                            df_result = pd.DataFrame(results)
                            cols = ['Status'] + [c for c in df_result.columns if c != 'Status']
                            df_result = df_result[cols]
                            all_results[sheet] = df_result
                        else:
                            all_results[sheet] = pd.DataFrame()
                            
                        progress_bar.progress((i + 1) / len(selected_sheets))
                    
                    # --- 5. ВЫВОД ---
                    st.subheader("Результат")
                    for sheet, df_res in all_results.items():
                        count = len(df_res)
                        if count == 0:
                            st.success(f"✅ Вкладка '{sheet}': Идентична (с учетом исключений и сортировки).")
                        else:
                            st.info(f"📄 Вкладка: {sheet} (Найдено изменений: {count})")
                            st.dataframe(df_res, use_container_width=True)
                            
                            csv = df_res.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label=f"📥 Скачать {sheet}",
                                data=csv,
                                file_name=f'result_{sheet}.csv',
                                mime='text/csv',
                                key=f'dl_{sheet}'
                            )

    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.error(str(e))

else:
    st.info("Загрузите файлы.")
