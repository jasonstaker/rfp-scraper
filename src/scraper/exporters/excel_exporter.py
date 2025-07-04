# excel_exporter.py
import math
import logging
import pandas as pd
from PIL import Image

from scraper.utils.date_utils import parse_date_generic
from scraper.utils.date_utils import filter_by_dates
from src.config import ASSETS_DIR

# initialize logger
logger = logging.getLogger(__name__)

# requires: original_df is a pandas DataFrame, state_name is a string
# modifies: nothing
# effects: returns a new DataFrame formatted for Excel with specified columns
def get_final_excel(original_df, state_name):
    state_title = state_name.capitalize()
    return pd.DataFrame({
        '': '',  # placeholder for checkbox
        'Proposal title': original_df['title'],
        'State': state_title,
        'Solicitation #': original_df['code'],
        'Due Date': original_df['end_date'].apply(parse_date_generic),
        'Keyword Hits': original_df['Keyword Hits'],
        'Link': original_df['link']
    })

# requires: state_to_df_map is a dictionary mapping state names to DataFrames, writer is an ExcelWriter object
# modifies: the Excel file through the writer
# effects: processes state DataFrames, concatenates them, filters by dates, and writes to an Excel sheet with custom formatting
def export_all(state_to_df_map, writer):
    logger.info("Starting Excel export")
    logger.info("Processing state data")
    all_chunks = []
    for state_name, orig_df in state_to_df_map.items():
        deduped = orig_df.drop_duplicates()
        chunk = get_final_excel(deduped, state_name)
        all_chunks.append(chunk)

    # concatenate all states into one DataFrame
    all_final = filter_by_dates(pd.concat(all_chunks, ignore_index=True))

    # write to a single sheet called "All RFPs"
    logger.info("Writing to Excel sheet 'All RFPs'")
    sheet_name = "All RFPs"
    all_final.to_excel(writer, sheet_name=sheet_name, index=False)
    workbook = writer.book
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
    white_fill = workbook.add_format({'bg_color': 'white'})

    for col_idx, col_name in enumerate(all_final.columns):
        worksheet.write(0, col_idx, col_name, header_fmt)
    worksheet.write_blank('A1', None, white_fill)
    worksheet.set_row(0, 40)

    # add autofilter on the "State" column
    last_row = all_final.shape[0]
    worksheet.autofilter(0, 1, last_row, 5)

    # column widths
    worksheet.set_column('A:A', 20)
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
        'valign':     'vcenter',
        'bg_color':   '#8388C1',
        'bold':       True,
        'text_wrap':  True,
        'border':     5
    })
    default_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'align':      'center',
        'valign':     'vcenter',
        'text_wrap':  True,
        'border':     2
    })
    default_blue_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'align':      'center',
        'valign':     'vcenter',
        'text_wrap':  True,
        'border':     2,
        'bg_color':   "#DAE9F8"
    })
    italic_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'italic':     True,
        'align':      'center',
        'text_wrap':  True,
        'valign':     'vcenter',
        'border':     2
    })
    italic_blue_fmt = workbook.add_format({
        'font_name':  'Aptos Narrow',
        'font_size':  11,
        'font_color': 'black',
        'italic':     True,
        'align':      'center',
        'text_wrap':  True,
        'valign':     'vcenter',
        'border':     2,
        'bg_color':   "#DAE9F8"
    })
    link_fmt = workbook.add_format({
        'text_wrap': True,
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

    # insert image (now using ASSETS_DIR)
    logo_path = ASSETS_DIR / "hotb_logo.jpg"
    img = Image.open(str(logo_path))
    img_width, img_height = img.size

    scale = 311 / 858
    y_offset = (107 - 71) / 4

    worksheet.insert_image('A1', str(logo_path), {
        'x_scale': scale,
        'y_scale': scale,
        'y_offset': y_offset
    })

    logger.info("Completed Excel export")