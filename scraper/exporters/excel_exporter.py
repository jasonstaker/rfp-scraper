# excel_exporter.py
import math
import os
import pandas as pd

def get_final_excel(original_df, state_name):
    state_title = state_name.capitalize()

    return pd.DataFrame({
        'Hide': '', # placeholder for checkbox
        'Proposal title': original_df['Label'],
        'State': state_title,
        'Solicitation #': original_df['Code'],
        'Due Date': original_df['End (UTC-7)'],
        'Keyword Hits': original_df['Keyword Hits'],
        'Link': original_df['Link']
    })


def export_all(state_to_df_map, writer):
    # collect each state's DataFrame, drop duplicates, and reshape for Excel
    all_chunks = []
    for state_name, orig_df in state_to_df_map.items():
        deduped = orig_df.drop_duplicates()
        chunk = get_final_excel(deduped, state_name)
        all_chunks.append(chunk)

    # concatenate all states into one DataFrame
    all_final = pd.concat(all_chunks, ignore_index=True)

    # write to a single sheet called "All RFPs"
    sheet_name = "All RFPs"
    all_final.to_excel(writer, sheet_name=sheet_name, index=False)
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]

    # header formatting
    header_fmt = workbook.add_format({
        'bold':       True,
        'text_wrap':  True,
        'valign':     'vcenter',
        'align':      'center',
        'fg_color':   '#1A429A',
        'font_color': 'white',
        'border':     5,
        'font_size':  14,
        'font_name':  'Aptos Narrow Bold'
    })
    for col_idx, col_name in enumerate(all_final.columns):
        worksheet.write(0, col_idx, col_name, header_fmt)
    worksheet.set_row(0, 66)

    # add autofilter on the "State" column
    last_row = all_final.shape[0]
    worksheet.autofilter(0, 2, last_row, 2)

    # column widths
    worksheet.set_column('A:A', 8)
    worksheet.set_column('B:B', 41)
    worksheet.set_column('C:C', 14.5)
    worksheet.set_column('D:D', 30.5)
    worksheet.set_column('E:E', 24)
    worksheet.set_column('F:F', 10)
    worksheet.set_column('G:G', 60)

    # row formats
    wrap_yellow_fmt = workbook.add_format({
        'font_name':   'Aptos Narrow',
        'font_size':   11,
        'font_color':  'black',
        'align':       'center',
        'valign':      'vcenter',
        'bg_color':    '#FFD486',
        'bold':        True,
        'text_wrap':   True,
        'border':      5
    })
    wrap_blue_fmt = workbook.add_format({
        'font_name':   'Aptos Narrow',
        'font_size':   11,
        'font_color':  'black',
        'align':       'center',
        'valign':      'vcenter',
        'bg_color':    '#8388C1',
        'bold':        True,
        'text_wrap':   True,
        'border':      5
    })
    default_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'align':      'center',
        'valign':     'vcenter',
        'border':     2
    })
    default_blue_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'align':      'center',
        'valign':     'vcenter',
        'border':     2,
        'bg_color': "#DAE9F8"
    })
    italic_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'italic':     True,
        'align':      'center',
        'valign':     'vcenter',
        'border':     2
    })
    italic_blue_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'italic':     True,
        'align':      'center',
        'valign':     'vcenter',
        'border':     2,
        'bg_color': "#DAE9F8"
    })
    link_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': '#0563C1',
        'underline':  True,
        'align':      'center',
        'valign':     'vcenter',
        'border':     2
    })

    # write data rows with alternating wrap colors per state
    toggle_blue = True
    prev_state = None
    for row_idx, row in enumerate(all_final.itertuples(index=False), start=1):
        state = row[2]  # State column
        if state != prev_state:
            toggle_blue = not toggle_blue
            prev_state = state

        blue_fill = workbook.add_format({
            'bg_color': "#1A429A",
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 2
        })
        worksheet.insert_checkbox(row_idx, 0, False, blue_fill)

        for col_idx, cell_val in enumerate(row, start=0):
            if col_idx == 0:
                continue
            # choose format
            if col_idx == 1:      # Proposal title
                fmt = wrap_blue_fmt if toggle_blue else wrap_yellow_fmt
            elif col_idx == 3:
                fmt = italic_blue_fmt
            elif col_idx == 4:
                fmt = italic_fmt
            elif col_idx == 5:
                fmt = default_blue_fmt
            elif col_idx == 6:
                fmt = link_fmt
            else:
                fmt = default_fmt

            # hyperlink for Link column
            if col_idx == 6:
                worksheet.write_url(row_idx, col_idx, cell_val or "", fmt)
            else:
                worksheet.write(row_idx, col_idx, cell_val, fmt)

        # adjust row height based on title length
        title = row[1]
        lines = math.ceil(len(str(title)) / 41)
        height = max(lines * 15, 40)
        worksheet.set_row(row_idx, height)

    # conditional formatting grey fill when checkbox is true
    grey_fill = workbook.add_format({'bg_color': "#5D5C5C"})
    last_row = all_final.shape[0]
    worksheet.conditional_format(1, 1, last_row, 6, {
        'type':     'formula',
        'criteria': '=INDIRECT("A"&ROW())=TRUE',
        'format':   grey_fill
    })
