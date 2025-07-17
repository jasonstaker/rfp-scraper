QWidget {
    background-color: #FFFFFF;
    color: #1A429A;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    font-size: ${font_size_base};
}

QLabel, QPushButton, QListWidget, QTableWidget, QPlainTextEdit {
    color: #1A429A;
}

QPushButton:focus {
    outline: none;
}

#header_bar {
    background-color: #1A429A;
    border-bottom: 2px solid #8388C1;
    padding: ${padding_header};
}

#header_bar QLabel {
    color: #FFFFFF;
    font-weight: bold;
    letter-spacing: 1px;
}

QPushButton {
    background-color: #1A429A;
    color: #FFFFFF;
    border: none;
    border-radius: ${border_radius};
    padding: ${padding_button_v} ${padding_button_h};
    min-height: ${min_button_height};
    font-size: ${font_size_button};
    font-weight: 600;
}

QPushButton:hover {
    background-color: #8388C1;
}
QPushButton:pressed {
    background-color: #FFD486;
    color: #1A429A;
}
QPushButton:disabled {
    background-color: #CCCCCC;
    color: #777777;
}

#code_editor {
    background-color: #F5F5F5;
    border: 2px solid #8388C1;
    border-radius: ${border_radius};
    padding: ${padding_code};
    selection-background-color: #FFD486;
    selection-color: #1A429A;
    qproperty-frameShadow: Raised;
}

LineNumberArea {
    background-color: #1A429A;
    color: #FFFFFF;
    padding-right: ${padding_button_h};
}

#code_editor QPlainTextEdit::ExtraSelection {
    background-color: #FFF7E0;
}

#state_list {
    background-color: #FFFFFF;
    border: 2px solid #8388C1;
    border-radius: ${border_radius};
    padding: ${padding_code};
}

#state_list::item {
    padding: ${padding_button_v} ${padding_button_h};
    margin: 2px 0;
    border-radius: 4px;
}
#state_list::item:hover {
    background-color: #E0E0E0;
}
#state_list::item:selected {
    background-color: #FFD486;
    color: #1A429A;
}

QScrollBar:vertical {
    background: #F5F5F5;
    width: ${scrollbar_width};
    border-radius: ${border_radius_scroll};
    border: none;
}
QScrollBar::handle:vertical {
    background: #8388C1;
    min-height: ${scrollbar_minlen};
    border-radius: ${border_radius_scroll};
}
QScrollBar::handle:vertical:hover {
    background: #6B6FA8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #F5F5F5;
    height: ${scrollbar_width};
    border-radius: ${border_radius_scroll};
    border: none;
}
QScrollBar::handle:horizontal {
    background: #8388C1;
    min-width: ${scrollbar_minlen};
    border-radius: ${border_radius_scroll};
}
QScrollBar::handle:horizontal:hover {
    background: #6B6FA8;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

#status_table {
    background-color: #FFFFFF;
    border: 2px solid #8388C1;
    border-radius: ${border_radius};
    gridline-color: #E0E0E0;
}

QTableCornerButton {
    background-color: #1A429A;
    border: none;
}

#status_table QHeaderView::section {
    background-color: #1A429A;
    color: #FFFFFF;
    border: none;
    padding: ${padding_table};
    font-weight: bold;
    font-size: ${font_size_table_head};
    text-transform: uppercase;
    letter-spacing: 1px;
    qproperty-alignment: 'AlignHCenter';
}

#status_table::item:!selected:alternate {
    background-color: #F9F9FB;
}

#status_table::item {
    padding: ${padding_button_v} ${padding_cell};
    font-size: ${font_size_cell};
    qproperty-textAlignment: 'AlignHCenter';
}

#status_table::item:selected {
    background-color: #FFD486;
    color: #1A429A;
}

#log_output {
    background-color: #F5F5F5;
    border: 2px solid #8388C1;
    border-radius: ${border_radius};
    padding: ${padding_code};
    font-size: ${font_size_cell};
    selection-background-color: #FFD486;
    selection-color: #1A429A;
    qproperty-frameShadow: Raised;
}

#status_header_label {
    font-size: ${font_size_header};
    font-weight: 700;
    color: #1A429A;
    margin: ${padding_cell} 0;
    qproperty-alignment: 'AlignHCenter';
}

#run_info_label {
    font-size: ${font_size_subheader};
    font-style: italic;
    color: #1A429A;
    margin: ${padding_code} 0;
    qproperty-alignment: 'AlignHCenter';
}

#status_error_label {
    color: red;
    font-size: ${font_size_error};
    margin-bottom: ${padding_code};
    qproperty-alignment: 'AlignHCenter';
}

QWidget:focus {
    outline: ${outline_width} solid #FFD486;
    outline-offset: ${outline_offset};
}
