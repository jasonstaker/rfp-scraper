# excel_exporter.py

import math
import logging
import pandas as pd
from scraper.utils.data_utils import split_by_keywords
from scraper.utils.date_utils import filter_by_dates, parse_date_generic
from scraper.utils.text_utils import sanitize
from src.config import ASSETS_DIR

logger = logging.getLogger(__name__)


# requires: state_to_df_map is dict[str, DataFrame], writer is ExcelWriter
# modifies: writes two sheets to the writer, but does not apply styling
# effects: orchestrates raw assembly, cleaning, formatting, sheet writing, and styling
def export_all(state_to_df_map: dict[str, pd.DataFrame], writer) -> None:
    try:
        raw_all = _assemble_raw_df(state_to_df_map)
        visible_raw, hidden_raw = _clean_and_split(raw_all)
        visible, hidden = _format_for_excel(visible_raw), _format_for_excel(hidden_raw)
        _write_tables(writer, visible, hidden)
        formats = _build_formats(writer.book)
        _apply_styles(writer, visible, hidden, formats)
    except Exception as e:
        logger.exception(f"Non-fatal error in export_all: {e}")
        
        try:
            pd.DataFrame().to_excel(writer, sheet_name="All RFPs", index=False)
            pd.DataFrame().to_excel(writer, sheet_name="Hidden RFPs", index=False)
        except Exception:
            logger.error("Failed to write fallback sheets")


# requires: map of state→DataFrame
# effects: returns concatenated, deduplicated, sanitized DataFrame with 'state'
def _assemble_raw_df(state_to_df_map: dict[str, pd.DataFrame]) -> pd.DataFrame:
    raws = []
    for state, df in state_to_df_map.items():
        df2 = df.drop_duplicates().copy()
        df2['state'] = state
        for col in df2.select_dtypes(include='object').columns:
            df2[col] = df2[col].apply(sanitize)
        raws.append(df2)
    return pd.concat(raws, ignore_index=True) if raws else pd.DataFrame()


# requires: raw_all DataFrame
# effects: splits by keywords and filters by dates
def _clean_and_split(raw_all: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        vis, hid = split_by_keywords(raw_all)
        return filter_by_dates(vis), filter_by_dates(hid)
    except Exception as e:
        logger.error(f"Error in cleaning/splitting data: {e}")
        return raw_all, pd.DataFrame()


# requires: cleaned DataFrame
# effects: renames/parses for Excel output
def _format_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        '': '',
        'Proposal title': df.get('title', pd.Series()),
        'State': df.get('state', pd.Series()).str.capitalize().fillna(''),
        'Solicitation #': df.get('code', pd.Series()),
        'Due Date': df.get('end_date', pd.Series()).apply(parse_date_generic),
        'Keyword Hits': df.get('Keyword Hits', pd.Series()),
        'Link': df.get('link', pd.Series())
    })


# requires: writer, visible, hidden
# modifies: writes sheets without styling
def _write_tables(writer, visible: pd.DataFrame, hidden: pd.DataFrame) -> None:
    visible.to_excel(writer, sheet_name="All RFPs", index=False)
    hidden.to_excel(writer, sheet_name="Hidden RFPs", index=False)


# requires: workbook
# effects: builds/caches all workbook formats to preserve original styling
def _build_formats(workbook):
    f = {}
    # header
    f['header'] = workbook.add_format({
        'bold': True,'text_wrap': True,'valign': 'vcenter','align': 'center',
        'fg_color': '#1A429A','font_color': 'white','border': 5,
        'font_size': 14,'font_name': 'Aptos Narrow Bold'
    })
    # row fills
    f['wrap_yellow'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black',
        'align': 'center','valign': 'vcenter','bg_color': '#FFD486',
        'bold': True,'text_wrap': True,'border': 5
    })
    f['wrap_blue'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black',
        'align': 'center','valign': 'vcenter','bg_color': '#8388C1',
        'bold': True,'text_wrap': True,'border': 5
    })
    f['default'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black',
        'align': 'center','valign': 'vcenter','text_wrap': True,'border': 2
    })
    f['default_blue'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black',
        'align': 'center','valign': 'vcenter','text_wrap': True,'border': 2,
        'bg_color': '#DAE9F8'
    })
    f['italic'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black','italic': True,
        'align': 'center','valign': 'vcenter','text_wrap': True,'border': 2
    })
    f['italic_blue'] = workbook.add_format({
        'font_name': 'Aptos Narrow','font_size': 11,'font_color': 'black','italic': True,
        'align': 'center','valign': 'vcenter','text_wrap': True,'border': 2,
        'bg_color': '#DAE9F8'
    })
    f['link'] = workbook.add_format({
        'text_wrap': True,'font_name': 'Aptos Narrow','font_size': 11,
        'font_color': '#0563C1','underline': True,'align': 'center','valign': 'vcenter','border': 2
    })
    f['checkbox'] = workbook.add_format({
        'bg_color': '#1A429A','font_color': 'white','align': 'center','valign': 'vcenter','border': 2
    })
    f['grey_fill'] = workbook.add_format({'bg_color': '#5D5C5C'})
    return f


# requires: writer, visible, hidden, formats dict
# modifies: applies all formatting, logos, checkboxes, conditional formats
def _apply_styles(writer, visible: pd.DataFrame, hidden: pd.DataFrame, f):
    wb = writer.book
    logo = ASSETS_DIR / 'hotb_logo.jpg'
    scale, y_offset = 311/858, (107-71)/4
    for name, df in [('All RFPs', visible), ('Hidden RFPs', hidden)]:
        ws = writer.sheets[name]
        
        for col_idx, col in enumerate(df.columns): ws.write(0, col_idx, col, f['header'])
        ws.set_row(0, 40)
        
        last = df.shape[0]
        ws.autofilter(0, 1, last, 5)
        ws.set_column('A:A', 20); ws.set_column('B:B', 41)
        ws.set_column('C:C', 14.5); ws.set_column('D:D', 30.5)
        ws.set_column('E:E', 24); ws.set_column('F:F', 10); ws.set_column('G:G', 60)
        ws.write_blank('A1', None, wb.add_format({'bg_color': 'white'}))
        ws.insert_image('A1', str(logo), {'x_scale': scale, 'y_scale': scale, 'y_offset': y_offset})
        
        toggle = True; prev = None
        for i, row in enumerate(df.itertuples(index=False), start=1):
            state = row[2]
            if state != prev: toggle = not toggle; prev = state
            ws.insert_checkbox(i, 0, False, f['checkbox'])
            for j, val in enumerate(row):
                if j == 0: continue
                if j == 1: fmt = f['wrap_blue'] if toggle else f['wrap_yellow']
                elif j == 3: fmt = f['italic_blue']
                elif j == 4: fmt = f['italic']
                elif j == 5: fmt = f['default_blue']
                elif j == 6: fmt = f['link']
                else: fmt = f['default']
                if j == 6:
                    ws.write_url(i, j, val or "", fmt)
                else:
                    ws.write(i, j, val, fmt)
            
            lines = math.ceil(len(str(row[1])) / 41)
            ws.set_row(i, max(lines * 15, 40))
        
        ws.conditional_format(1, 1, last, 6, {
            'type': 'formula', 'criteria': '=INDIRECT("A"&ROW())=TRUE', 'format': f['grey_fill']
        })
    logger.info("Completed Excel export")
