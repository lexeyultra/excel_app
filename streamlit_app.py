import streamlit as st
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="Сравнение Excel с игнорированием столбцов", layout="wide")

st.title("📊 Сравнение Excel (Игнорирование столбцов)")
st.markdown("""
Приложение находит новые и измененные данные во втором файле.
Вы можете выбрать столбцы, которые нужно **игнорировать** при сравнении (например, дату обновления).
* 🟢 **Добавлено**: Строка есть во втором файле, но отсутствует в первом.
* 🟡 **Изменено**: Строка есть в обоих, но значения (кроме игнорируемых) отличаются.
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
            st.subheader("Шаг 1: Выберите вкладки")
            selected_sheets = st.multiselect("Выберите вкладки:", common_sheets, default=common_sheets)
            
            # --- НОВАЯ ФУНКЦИЯ: ВЫБОР СТОЛБЦОВ ДЛЯ ИГНОРИРОВАНИЯ ---
            ignored_cols_map = {} # Словарь: {имя_вкладки: [список_игнорируемых_колонок]}
            
            if selected_sheets:
                st.subheader("Шаг 2: Выберите столбцы для игнорирования")
                st.info("Если в списке ничего не выбрано, сравниваются все столбцы.")
                
                # Для каждой выбранной вкладки создаем свой выборщик
                for sheet in selected_sheets:
                    # Читаем только заголовки, чтобы получить список колонок
                    # nrows=1 ускоряет чтение, так как нам нужны только названия колонок
                    df_preview = pd.read_excel(xls1, sheet_name=sheet, nrows=1)
                    columns = df_preview.columns.tolist()
                    
                    # multiselect позволяет выбрать несколько колонок
                    ignored = st.multiselect(
                        f"Игнорировать столбцы во вкладке '{sheet}':", 
                        columns, 
                        key=f"ignore_{sheet}", # уникальный ключ для виджета
                        help="Эти колонки не будут учитываться при поиске различий"
                    )
                    ignored_cols_map[sheet] = ignored
            
            # --- 3. КНОПКА ЗАПУСКА ---
            if st.button("🔍 Найти различия (с учетом игнорируемых колонок)"):
                if not selected_sheets:
                    st.warning("Выберите вкладки.")
                else:
                    all_results = {}
                    progress_bar = st.progress(0)
                    
                    # --- 4. ЛОГИКА СРАВНЕНИЯ ---
                    for i, sheet in enumerate(selected_sheets):
                        df1 = pd.read_excel(xls1, sheet_name=sheet).fillna('')
                        df2 = pd.read_excel(xls2, sheet_name=sheet).fillna('')
                        
                        df1.reset_index(drop=True, inplace=True)
                        df2.reset_index(drop=True, inplace=True)
                        
                        # Получаем список колонок, которые нужно игнорировать для этой вкладки
                        current_ignored = ignored_cols_map.get(sheet, [])
                        
                        # Формируем список колонок, по которым СРАВНИВАЕМ
                        # (все колонки минус игнорируемые)
                        cols_to_compare = [c for c in df1.columns if c not in current_ignored]
                        
                        max_rows = max(len(df1), len(df2))
                        results = []
                        
                        for row_idx in range(max_rows):
                            row_data = {}
                            status = ""
                            
                            # Логика НОВОЙ строки
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
                                
                                # Важно: В результат записываем ВСЕ колонки, но сравниваем только cols_to_compare
                                for col in df1.columns:
                                    val1 = df1.at[row_idx, col]
                                    val2 = df2.at[row_idx, col] if col in df2.columns else ""
                                    
                                    row_data[f"{col}_Day1"] = val1
                                    row_data[f"{col}_Day2"] = val2
                                    
                                    # ПРОВЕРКА: Если колонка не в списке игнорируемых -> сравниваем
                                    if col in cols_to_compare:
                                        if str(val1) != str(val2):
                                            is_different = True
                                
                                if is_different:
                                    status = "🟡 Изменено"
                                else:
                                    status = "⚪ Без изменений"
                            
                            # Фильтрация результата (только Новые и Измененные)
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
                    
                    # --- 5. ВЫВОД РЕЗУЛЬТАТА ---
                    st.subheader("Результат")
                    
                    for sheet, df_res in all_results.items():
                        if df_res.empty:
                            st.info(f"Вкладка **'{sheet}'**: Различий (с учетом исключений) не найдено.")
                        else:
                            with st.expander(f"Вкладка: {sheet} (Записей: {len(df_res)})"):
                                st.dataframe(df_res, use_container_width=True)
                                
                                csv = df_res.to_csv(index=False).encode('utf-8-sig')
                                st.download_button(
                                    label=f"📥 Скачать '{sheet}' (CSV)",
                                    data=csv,
                                    file_name=f'result_{sheet}.csv',
                                    mime='text/csv',
                                    key=f'dl_{sheet}'
                                )

    except Exception as e:
        st.error(f"Ошибка обработки: {e}")
        st.error(e) # Вывод текста ошибки для отладки

else:
    st.info("Загрузите два файла для начала работы.")
