# scraper/exporters/excel_exporter.py
import math
import os
import pandas as pd

def get_final_excel(original_df, state_name):
    df = pd.DataFrame({
        'Proposal title': original_df['Label'],
        'State': state_name,
        'Solicitation #': original_df['Code'],
        'RFx Type': '???',
        'Due Date': original_df['End (UTC-7)'],
        'Decision Date': '???',
        'Keyword Hits': original_df['Keyword Hits']
    })
    return df

def export(df, state_name, writer):
    # actually drop duplicates in place
    df = df.drop_duplicates()

    # reshape for Excel
    final = get_final_excel(df, state_name)

    # write to its own sheet
    sheet_name = f"{state_name} RFPs"
    final.to_excel(writer, sheet_name=sheet_name, index=False)
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]

    # header formatting (unchanged)
    header_fmt = workbook.add_format({
        'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
        'fg_color': '#83cceb', 'font_color': 'black', 'border': 5,
        'font_size': 14, 'font_name': 'Aptos Narrow Bold'
    })
    for col_num, col in enumerate(final.columns):
        worksheet.write(0, col_num, col, header_fmt)
    worksheet.set_row(0, 66)

    # column widths (unchanged)
    worksheet.set_column('A:A', 41)
    worksheet.set_column('B:B', 14.5)
    worksheet.set_column('C:C', 30.5)
    worksheet.set_column('E:E', 24)
    worksheet.set_column('F:F', 20)

    # row formats
    wrap_fmt = workbook.add_format({
        'font_name':'Aptos Narrow','font_size':11,'font_color':'black',
        'align':'center','valign':'vcenter','bg_color':'#dae9f8',
        'underline':True,'text_wrap':True,'border':5
    })
    default_fmt = workbook.add_format({
        'font_name':'Aptos Narrow','font_size':11,'font_color':'black',
        'align':'center','valign':'vcenter','border':2
    })
    italic_fmt = workbook.add_format({
        'font_name':'Aptos Narrow','font_size':11,'font_color':'black',
        'italic':True,'align':'center','valign':'vcenter','border':2
    })

    # write data rows
    for row_idx, row in enumerate(final.itertuples(index=False), start=1):
        for col_idx, val in enumerate(row):
            fmt = wrap_fmt if col_idx==0 else (italic_fmt if col_idx in (2,4,5) else default_fmt)
            worksheet.write(row_idx, col_idx, val, fmt)
        # adjust row height to wrap title
        title = row[0]
        lines = math.ceil(len(str(title)) / 41)
        height = max(lines * 15, 40)
        worksheet.set_row(row_idx, height)
