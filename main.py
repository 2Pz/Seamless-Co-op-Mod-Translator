import sys
import json
import re
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFileDialog, QMessageBox, QLineEdit,
                            QScrollArea, QProgressBar, QFrame, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDir
from PyQt6.QtGui import QColor, QPalette, QIcon
from deep_translator import GoogleTranslator

def get_application_path():
    """Get the path to the application directory"""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle
        return os.path.dirname(sys.executable)
    else:
        # If the application is run from a Python interpreter
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = get_application_path()
    return os.path.join(base_path, relative_path)

def clean_html(text, preserve_html=False):
    if preserve_html:
        # Only convert newlines and backslashes while preserving HTML
        text = text.replace('\\n', '\n')
        return text
    else:
        # Remove HTML tags and convert HTML entities for display
        text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
        text = text.replace('&quot;', '"')    # Convert quotes
        text = text.replace('\\n', '\n')      # Convert newlines
        text = text.replace('\\', '')         # Remove remaining backslashes
        return text

class ExpandableTextDialog(QDialog):
    def __init__(self, text, title="Text", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Text area
        self.text_edit = QTextEdit()
        self.text_edit.setText(clean_html(text))
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class EditableExpandableTextDialog(QDialog):
    def __init__(self, text, title="Edit Text", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Text area
        self.text_edit = QTextEdit()
        self.text_edit.setText(clean_html(text))
        layout.addWidget(self.text_edit)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_text(self):
        return self.text_edit.toPlainText()

class TranslationThread(QThread):
    progress = pyqtSignal(int)
    translation_done = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, texts_to_translate, target_lang):
        super().__init__()
        self.texts_to_translate = texts_to_translate
        self.target_lang = target_lang

    def run(self):
        translator = GoogleTranslator(source='auto', target=self.target_lang)
        total = len(self.texts_to_translate)
        
        for i, (key, text) in enumerate(self.texts_to_translate.items()):
            try:
                translated = translator.translate(str(text))
                self.translation_done.emit(key, translated)
            except Exception as e:
                print(f"Error translating {key}: {str(e)}")
            self.progress.emit(int((i + 1) * 100 / total))
        
        self.finished.emit()

class TranslationWidget(QFrame):
    def __init__(self, key, source_text, main_window, parent=None):
        super().__init__(parent)
        self.key = key
        self.main_window = main_window
        self.source_text_value = str(source_text)
        self.init_ui(key)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
    
    def init_ui(self, key):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Key label (20% width)
        key_label = QLabel(key)
        key_label.setWordWrap(True)
        key_label.setMinimumWidth(200)
        key_label.setMaximumWidth(200)
        layout.addWidget(key_label)
        
        # Source text preview (30% width)
        self.source_preview = QLineEdit()
        self.source_preview.setReadOnly(True)
        self.source_preview.setText(self.truncate_text(clean_html(self.source_text_value)))
        self.source_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.source_preview.mousePressEvent = self.show_source_dialog
        layout.addWidget(self.source_preview)
        
        # Translation text preview (30% width)
        self.translation_preview = QLineEdit()
        self.translation_preview.setText("")
        self.translation_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.translation_preview.mousePressEvent = self.show_translation_dialog
        layout.addWidget(self.translation_preview)
        
        # Individual translate button (10% width)
        translate_btn = QPushButton("Translate")
        translate_btn.setMaximumWidth(100)
        translate_btn.clicked.connect(self.translate_individual)
        layout.addWidget(translate_btn)
    
    def truncate_text(self, text, max_length=50):
        return text if len(text) <= max_length else text[:max_length] + "..."
    
    def show_source_dialog(self, event):
        dialog = ExpandableTextDialog(self.source_text_value, f"Source Text - {self.key}", self)
        dialog.text_edit.setHtml(clean_html(self.source_text_value, preserve_html=True))
        dialog.exec()
    
    def show_translation_dialog(self, event):
        dialog = EditableExpandableTextDialog(self.translation_preview.text(), f"Translation - {self.key}", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.translation_preview.setText(dialog.get_text())
    
    def translate_individual(self):
        try:
            target_lang = self.main_window.lang_combo.currentText()
            clean_text = clean_html(self.source_text_value)
            translated = GoogleTranslator(source='auto', target=target_lang).translate(clean_text)
            self.translation_preview.setText(translated)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Translation failed: {str(e)}")
    
    def get_translation(self):
        return self.translation_preview.text()
    
    def set_translation(self, text):
        self.translation_preview.setText(text)
        
    def mark_needs_translation(self, needs_translation):
        if needs_translation:
            self.source_preview.setProperty('needs-translation', True)
            self.source_preview.style().unpolish(self.source_preview)
            self.source_preview.style().polish(self.source_preview)
        else:
            self.source_preview.setProperty('needs-translation', False)
            self.source_preview.style().unpolish(self.source_preview)
            self.source_preview.style().polish(self.source_preview)
    
    def mark_missing_translation(self, missing):
        if missing:
            self.source_preview.setProperty('missing-translation', True)
            self.source_preview.style().unpolish(self.source_preview)
            self.source_preview.style().polish(self.source_preview)
        else:
            self.source_preview.setProperty('missing-translation', False)
            self.source_preview.style().unpolish(self.source_preview)
            self.source_preview.style().polish(self.source_preview)

    def matches_search(self, key_text="", source_text="", target_text=""):
        """Check if this widget matches the search criteria"""
        key_match = key_text.lower() in self.key.lower()
        source_match = source_text.lower() in clean_html(self.source_text_value).lower()
        target_match = target_text.lower() in self.translation_preview.text().lower()
        
        # If any search field is empty, consider it a match
        if not key_text:
            key_match = True
        if not source_text:
            source_match = True
        if not target_text:
            target_match = True
            
        return key_match and source_match and target_match

class TranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seamless Co-op Mod Manager Translator")
        self.setMinimumSize(1200, 800)
        
        # Set application icon
        icon_path = resource_path(os.path.join('assets', 'languages.png'))
        self.setWindowIcon(QIcon(icon_path))
        
        # Load reference English JSON
        try:
            json_path = resource_path('en.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                self.en_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load en.json: {str(e)}\nPath: {json_path}")
            sys.exit(1)
        
        self.all_keys = self.flatten_dict(self.en_data)
        self.translation_widgets = {}
        self.user_json_data = None
        
        self.init_ui()
        
        # Load external stylesheet
        try:
            style_path = resource_path('dark_style.qss')
            if not os.path.exists(style_path):
                QMessageBox.warning(self, "Warning", f"Could not find stylesheet at: {style_path}")
            else:
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    self.setStyleSheet(stylesheet)
                    # Apply stylesheet to the application
                    QApplication.instance().setStyleSheet(stylesheet)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error loading stylesheet: {str(e)}\nPath: {style_path}")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Top controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        # Key search
        key_search_label = QLabel("Search Key:")
        self.key_search = QLineEdit()
        self.key_search.setPlaceholderText("Search by key...")
        self.key_search.textChanged.connect(self.apply_search_filters)
        search_layout.addWidget(key_search_label)
        search_layout.addWidget(self.key_search)
        
        # Source text search
        source_search_label = QLabel("Search Source:")
        self.source_search = QLineEdit()
        self.source_search.setPlaceholderText("Search in source text...")
        self.source_search.textChanged.connect(self.apply_search_filters)
        search_layout.addWidget(source_search_label)
        search_layout.addWidget(self.source_search)
        
        # Target text search
        target_search_label = QLabel("Search Translation:")
        self.target_search = QLineEdit()
        self.target_search.setPlaceholderText("Search in translations...")
        self.target_search.textChanged.connect(self.apply_search_filters)
        search_layout.addWidget(target_search_label)
        search_layout.addWidget(self.target_search)
        
        controls_layout.addLayout(search_layout)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Target Language:")
        self.lang_combo = QComboBox()
        self.lang_search = QLineEdit()
        self.lang_search.setPlaceholderText("Search language...")
        self.lang_search.textChanged.connect(self.filter_languages)
        
        # Get available languages
        self.available_langs = GoogleTranslator().get_supported_languages()
        self.lang_combo.addItems(self.available_langs)
        
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_search)
        lang_layout.addWidget(self.lang_combo)
        controls_layout.addLayout(lang_layout)
        
        # File and translation controls
        btn_layout = QHBoxLayout()
        self.load_file_btn = QPushButton("Load Target Translation")
        self.translate_all_btn = QPushButton("Translate All")
        self.save_btn = QPushButton("Save Translation")
        
        self.load_file_btn.clicked.connect(self.load_translation_file)
        self.translate_all_btn.clicked.connect(self.translate_all)
        self.save_btn.clicked.connect(self.save_translation)
        
        btn_layout.addWidget(self.load_file_btn)
        btn_layout.addWidget(self.translate_all_btn)
        btn_layout.addWidget(self.save_btn)
        controls_layout.addLayout(btn_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(controls_layout)
        
        # Headers
        headers_layout = QHBoxLayout()
        headers = [
            ("Key", 20),
            ("Source Text (click to view)", 30),
            ("Translation (click to edit)", 30),
            ("Action", 10)
        ]
        for text, stretch in headers:
            label = QLabel(text)
            headers_layout.addWidget(label, stretch)
        main_layout.addLayout(headers_layout)
        
        # Scroll area for translations
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.translations_layout = QVBoxLayout(scroll_content)
        self.translations_layout.setSpacing(5)
        
        # Add translation widgets
        for key, value in self.all_keys.items():
            widget = TranslationWidget(key, value, self)
            self.translation_widgets[key] = widget
            self.translations_layout.addWidget(widget)
        
        # Add stretch to push widgets to the top
        self.translations_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Status
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
    
    def apply_search_filters(self):
        """Apply search filters to show/hide translation widgets"""
        key_text = self.key_search.text()
        source_text = self.source_search.text()
        target_text = self.target_search.text()
        
        visible_count = 0
        for widget in self.translation_widgets.values():
            matches = widget.matches_search(key_text, source_text, target_text)
            widget.setVisible(matches)
            if matches:
                visible_count += 1
        
        self.status_label.setText(f"Showing {visible_count} of {len(self.translation_widgets)} items")
    
    def filter_languages(self, text):
        self.lang_combo.clear()
        filtered_langs = [lang for lang in self.available_langs if text.lower() in lang.lower()]
        self.lang_combo.addItems(filtered_langs)
    
    def flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def unflatten_dict(self, dictionary):
        resultDict = dict()
        for key, value in dictionary.items():
            parts = key.split(".")
            d = resultDict
            for part in parts[:-1]:
                if part not in d:
                    d[part] = dict()
                d = d[part]
            d[parts[-1]] = value
        return resultDict

    def load_translation_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Translation File", "", "JSON files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.user_json_data = json.load(f)
                user_flattened = self.flatten_dict(self.user_json_data)
                
                # Update translation widgets
                for key, widget in self.translation_widgets.items():
                    if key in user_flattened:
                        widget.set_translation(str(user_flattened[key]))
                        source_text = widget.source_text_value
                        translated_text = str(user_flattened[key])
                        needs_translation = source_text == translated_text
                        widget.mark_needs_translation(needs_translation)
                        widget.mark_missing_translation(False)
                    else:
                        widget.set_translation("")
                        widget.mark_needs_translation(False)
                        widget.mark_missing_translation(True)
                
                self.status_label.setText(f"Loaded translation file: {file_name}")
                self.apply_search_filters()  # Reapply search filters after loading
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def translate_all(self):
        target_lang = self.lang_combo.currentText()
        
        # Prepare texts to translate
        texts_to_translate = {
            key: widget.source_text_value
            for key, widget in self.translation_widgets.items()
            if not widget.translation_preview.text() and widget.isVisible()  # Only translate visible empty fields
        }
        
        self.progress_bar.setVisible(True)
        self.translate_all_btn.setEnabled(False)
        
        # Create and start translation thread
        self.translation_thread = TranslationThread(texts_to_translate, target_lang)
        self.translation_thread.progress.connect(self.update_progress)
        self.translation_thread.translation_done.connect(self.update_translation)
        self.translation_thread.finished.connect(self.translation_finished)
        self.translation_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_translation(self, key, translated_text):
        if key in self.translation_widgets:
            self.translation_widgets[key].set_translation(translated_text)
    
    def translation_finished(self):
        self.progress_bar.setVisible(False)
        self.translate_all_btn.setEnabled(True)
        self.status_label.setText("All translations completed")
    
    def save_translation(self):
        # Collect all translations
        translations = {}
        for key, widget in self.translation_widgets.items():
            translated_text = widget.get_translation()
            if translated_text:  # Only save non-empty translations
                translations[key] = translated_text
        
        # Convert to nested structure
        output_data = self.unflatten_dict(translations)
        
        # Save to file
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Translation", "", "JSON files (*.json)")
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                self.status_label.setText(f"Saved translation to: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = TranslatorApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
