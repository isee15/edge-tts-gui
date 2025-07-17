import asyncio
import os
import sys

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QComboBox, QFileDialog,
                             QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QProgressBar, QPushButton, QTextEdit,
                             QVBoxLayout, QWidget, QSlider)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

import edge_tts

class TTSThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, text, voice, output_file, rate, volume, pitch):
        super().__init__()
        self.text = text
        self.voice = voice
        self.output_file = output_file
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def run(self):
        try:
            asyncio.run(self._save())
            self.finished.emit(f"成功保存到 {self.output_file}")
        except Exception as e:
            self.error.emit(str(e))

    async def _save(self):
        communicate = edge_tts.Communicate(
            self.text, self.voice, rate=self.rate, volume=self.volume, pitch=self.pitch
        )
        await communicate.save(self.output_file)

class BatchTTSThread(QThread):
    progress = pyqtSignal(int, int, str) # current, total, filename
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, files, voice, rate, volume, pitch):
        super().__init__()
        self.files = files
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    def run(self):
        try:
            asyncio.run(self._run_batch())
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    async def _run_batch(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            self.progress.emit(i, total_files, os.path.basename(file_path))
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                
                if not text:
                    continue

                output_file = os.path.splitext(file_path)[0] + ".mp3"
                communicate = edge_tts.Communicate(
                    text, self.voice, rate=self.rate, volume=self.volume, pitch=self.pitch
                )
                await communicate.save(output_file)
            except Exception as e:
                # Log error for a single file but continue with others
                print(f"处理文件 {file_path} 出错: {e}")
        self.progress.emit(total_files, total_files, "完成")


class TTSApp(QWidget):
    def __init__(self, voices):
        super().__init__()
        self.voices = voices
        self.player = None
        self.audio_output = None
        self.current_output_file = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('小夕TTS')
        self.setWindowIcon(QIcon('icon.ico'))
        self.setGeometry(100, 100, 500, 400)

        layout = QVBoxLayout()

        # Text input
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此输入文本...")
        layout.addWidget(self.text_edit)

        # File operations
        file_layout = QHBoxLayout()
        self.import_btn = QPushButton('导入 TXT')
        self.import_btn.clicked.connect(self.import_text)
        file_layout.addWidget(self.import_btn)
        
        self.batch_btn = QPushButton('批量转换 TXT 到 MP3')
        self.batch_btn.clicked.connect(self.batch_convert)
        file_layout.addWidget(self.batch_btn)
        layout.addLayout(file_layout)

        # TTS options
        options_layout = QGridLayout()
        options_layout.addWidget(QLabel('语音:'), 0, 0)
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([v['ShortName'] for v in self.voices if "zh-CN" in v['ShortName']])
        self.voice_combo.setCurrentText("zh-CN-XiaoyiNeural")
        options_layout.addWidget(self.voice_combo, 0, 1)

        options_layout.addWidget(QLabel('输出文件名:'), 1, 0)
        self.output_file_edit = QLineEdit("output.mp3")
        options_layout.addWidget(self.output_file_edit, 1, 1)

        # Rate Slider
        options_layout.addWidget(QLabel('语速 (rate):'), 2, 0)
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(-100, 100)
        self.rate_slider.setValue(0)
        self.rate_label = QLabel("+0%")
        self.rate_slider.valueChanged.connect(lambda v: self.rate_label.setText(f"{v:+}%"))
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(self.rate_slider)
        rate_layout.addWidget(self.rate_label)
        options_layout.addLayout(rate_layout, 2, 1)

        # Volume Slider
        options_layout.addWidget(QLabel('音量 (volume):'), 3, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(-100, 100)
        self.volume_slider.setValue(0)
        self.volume_label = QLabel("+0%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v:+}%"))
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        options_layout.addLayout(volume_layout, 3, 1)

        # Pitch Slider
        options_layout.addWidget(QLabel('音调 (pitch):'), 4, 0)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-50, 50)
        self.pitch_slider.setValue(0)
        self.pitch_label = QLabel("+0Hz")
        self.pitch_slider.valueChanged.connect(lambda v: self.pitch_label.setText(f"{v:+}Hz"))
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(self.pitch_slider)
        pitch_layout.addWidget(self.pitch_label)
        options_layout.addLayout(pitch_layout, 4, 1)


        layout.addLayout(options_layout)

        # Action buttons
        action_layout = QHBoxLayout()
        self.generate_btn = QPushButton('生成 MP3')
        self.generate_btn.clicked.connect(self.generate_tts)
        action_layout.addWidget(self.generate_btn)

        self.play_btn = QPushButton('播放')
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setEnabled(False)
        action_layout.addWidget(self.play_btn)
        
        layout.addLayout(action_layout)


        # Progress and status
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel('准备就绪')
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def import_text(self):
        file_name, _ = QFileDialog.getOpenFileName(self, '打开 TXT 文件', '', 'Text Files (*.txt)')
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    self.text_edit.setText(f.read())
                self.status_label.setText(f"已导入 {os.path.basename(file_name)}")
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法加载文件: {e}')

    def generate_tts(self):
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, '警告', '文本内容不能为空')
            return

        self.play_btn.setEnabled(False)
        self.play_btn.setText("播放")
        if self.player and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        voice = self.voice_combo.currentText()
        output_file = self.output_file_edit.text().strip()
        if not output_file.endswith(".mp3"):
            output_file += ".mp3"
        
        self.current_output_file = output_file

        rate = self.rate_label.text()
        volume = self.volume_label.text()
        pitch = self.pitch_label.text()
        
        self.generate_btn.setEnabled(False)
        self.status_label.setText('正在生成...')
        self.progress_bar.setRange(0, 0) # Indeterminate progress

        self.tts_thread = TTSThread(text, voice, output_file, rate, volume, pitch)
        self.tts_thread.finished.connect(self.on_tts_finished)
        self.tts_thread.error.connect(self.on_tts_error)
        self.tts_thread.start()

    def on_tts_finished(self, message):
        self.status_label.setText(message)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.play_btn.setEnabled(True)
        self.init_player()
        QMessageBox.information(self, '成功', message)

    def on_tts_error(self, error_message):
        self.status_label.setText(f'错误: {error_message}')
        self.generate_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, '错误', f'生成失败: {error_message}')

    def batch_convert(self):
        files, _ = QFileDialog.getOpenFileNames(self, '选择要转换的 TXT 文件', '', 'Text Files (*.txt)')
        if not files:
            return

        self.play_btn.setEnabled(False)
        self.play_btn.setText("播放")
        if self.player and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        voice = self.voice_combo.currentText()
        rate = self.rate_label.text()
        volume = self.volume_label.text()
        pitch = self.pitch_label.text()
        
        self.batch_btn.setEnabled(False)
        self.generate_btn.setEnabled(False)
        self.status_label.setText("开始批量转换...")

        self.batch_thread = BatchTTSThread(files, voice, rate, volume, pitch)
        self.batch_thread.progress.connect(self.update_batch_progress)
        self.batch_thread.finished.connect(self.on_batch_finished)
        self.batch_thread.error.connect(self.on_batch_error)
        self.batch_thread.start()

    def update_batch_progress(self, current, total, filename):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"正在处理 ({current}/{total}): {filename}")

    def on_batch_finished(self):
        self.status_label.setText("批量转换完成")
        self.batch_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())
        QMessageBox.information(self, '成功', "所有文件已成功转换。")

    def on_batch_error(self, error_message):
        self.status_label.setText(f'批量转换出错: {error_message}')
        self.batch_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, '错误', f'批量转换失败: {error_message}')

    def init_player(self):
        if not self.player:
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        source = QUrl.fromLocalFile(os.path.abspath(self.current_output_file))
        self.player.setSource(source)

    def toggle_play(self):
        if not self.player:
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty():
                 self.init_player()
            self.player.play()

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("暂停")
        else:
            self.play_btn.setText("播放")


async def get_voices():
    return await edge_tts.list_voices()

def main():
    app = QApplication(sys.argv)

    # Apply a modern stylesheet
    style_sheet = """
        QWidget {
            background-color: #2c3e50;
            color: #ecf0f1;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:disabled {
            background-color: #95a5a6;
        }
        QTextEdit, QLineEdit {
            background-color: #34495e;
            border: 1px solid #2c3e50;
            border-radius: 5px;
            padding: 5px;
        }
        QComboBox {
            background-color: #34495e;
            border: 1px solid #2c3e50;
            border-radius: 5px;
            padding: 5px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: url(down_arrow.png); /* You might need to create a small down arrow icon */
        }
        QLabel {
            color: #bdc3c7;
        }
        QProgressBar {
            border: 1px solid #34495e;
            border-radius: 5px;
            text-align: center;
            background-color: #34495e;
        }
        QProgressBar::chunk {
            background-color: #27ae60;
            border-radius: 4px;
        }
        QMessageBox {
            background-color: #34495e;
        }
    """
    app.setStyleSheet(style_sheet)
    
    # Get voices and then create the app
    loop = asyncio.get_event_loop()
    voices = loop.run_until_complete(get_voices())
    
    ex = TTSApp(voices)
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
