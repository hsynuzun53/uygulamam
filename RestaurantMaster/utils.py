import pandas as pd
import streamlit as st
from datetime import datetime
import io

def export_to_excel(df, start_date=None, end_date=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Stok Raporu', index=False, startrow=2)

        workbook = writer.book
        worksheet = writer.sheets['Stok Raporu']

        # Başlık formatı
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'border': 1,
            'bg_color': '#D7E4BC'
        })

        # Tarih başlığı formatı
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'border': 0
        })

        # Tarih aralığı başlığı
        if start_date and end_date:
            title = f"Stok Raporu\n{start_date} - {end_date}"
            worksheet.merge_range('A1:F1', title, title_format)

        # Veri hücresi formatları
        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True
        })

        number_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': 'dd.mm.yyyy hh:mm'
        })

        # Başlıkları formatla
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(2, col_num, value, header_format)

        # Veri hücrelerini formatla
        for row in range(len(df)):
            for col in range(len(df.columns)):
                value = df.iloc[row, col]
                col_name = df.columns[col]

                if 'TARİH' in col_name:
                    worksheet.write(row + 3, col, value, date_format)
                elif isinstance(value, (int, float)) and ('FİYAT' in col_name or 'MİKTAR' in col_name):
                    worksheet.write(row + 3, col, value, number_format)
                else:
                    worksheet.write(row + 3, col, value, cell_format)

        # Sütun genişliklerini ayarla
        for idx, col in enumerate(df.columns):
            series = df[col]
            max_len = max(
                series.astype(str).apply(len).max(),
                len(str(series.name))
            ) + 2
            worksheet.set_column(idx, idx, max_len)

        # Satır yüksekliğini ayarla
        worksheet.set_default_row(20)
        worksheet.set_row(2, 25)  # Başlık satırı için ekstra yükseklik

    return output.getvalue()

def format_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
