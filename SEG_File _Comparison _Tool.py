import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QLineEdit, QPushButton, QFileDialog, QTreeWidget,
                             QTreeWidgetItem, QTabWidget, QTextEdit, QHeaderView, QMessageBox,
                             QGroupBox, QComboBox, QRadioButton, QProgressBar, QDialog,
                             QScrollArea, QFrame, QToolBar, QStatusBar, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QBrush, QFont, QIcon


class ModernButton(QPushButton):
    def __init__(self, text, parent=None, primary=False):
        super().__init__(text, parent)
        self.setMinimumHeight(38)
        self.setCursor(Qt.PointingHandCursor)
        self.primary = primary
        self.set_style()

    def set_style(self, color="#0084FF"):
        if self.primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-weight: 600;
                    font-size: 14px;
                    min-height: 38px;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(color)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(color)};
                }}
                QPushButton:disabled {{
                    background-color: #E8E8E8;
                    color: #A0A0A0;
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #333333;
                    border: 1.5px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: 500;
                    font-size: 13px;
                    min-height: 36px;
                }
                QPushButton:hover {
                    background-color: #EDEDED;
                    border-color: #D0D0D0;
                }
                QPushButton:pressed {
                    background-color: #E0E0E0;
                }
            """)

    def lighten_color(self, color):
        qcolor = QColor(color)
        return qcolor.lighter(115).name()

    def darken_color(self, color):
        qcolor = QColor(color)
        return qcolor.darker(115).name()


class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 12px 16px;
                font-weight: 500;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
            QPushButton:checked {
                background-color: #E6F3FF;
                color: #0084FF;
                font-weight: 600;
            }
        """)


class DirectoryInput(QWidget):
    def __init__(self, placeholder="选择目录...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                border: 1.5px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px 12px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0084FF;
            }
        """)
        layout.addWidget(self.line_edit)

        self.browse_btn = ModernButton("浏览")
        self.browse_btn.setFixedWidth(70)
        layout.addWidget(self.browse_btn)

    def text(self):
        return self.line_edit.text()

    def setText(self, text):
        self.line_edit.setText(text)


class ComparisonWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    file_processed = pyqtSignal(str)

    def __init__(self, true_dir, pred_dir):
        super().__init__()
        self.true_dir = true_dir
        self.pred_dir = pred_dir

    def run(self):
        try:
            results = self.compare_seg_directories(self.true_dir, self.pred_dir)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

    def get_seg_files(self, directory):
        return {f for f in os.listdir(directory) if f.lower().endswith('.seg')}

    def read_labels(self, filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]

    def compare_labels(self, true_labels, pred_labels):
        mismatches = []
        min_len = min(len(true_labels), len(pred_labels))

        for i in range(min_len):
            if true_labels[i] != pred_labels[i]:
                mismatches.append(i)

        length_diff = len(true_labels) - len(pred_labels)
        return mismatches, abs(length_diff)

    def compare_seg_directories(self, true_dir, pred_dir):
        true_files = self.get_seg_files(true_dir)
        pred_files = self.get_seg_files(pred_dir)

        common_files = true_files & pred_files
        if not common_files:
            self.error.emit("两个目录下没有相同名称的.seg文件")
            return {}

        results = {}
        total_files = len(common_files)

        for i, filename in enumerate(sorted(common_files)):
            true_path = os.path.join(true_dir, filename)
            pred_path = os.path.join(pred_dir, filename)

            try:
                true_labels = self.read_labels(true_path)
                pred_labels = self.read_labels(pred_path)
            except Exception as e:
                continue

            mismatches, length_diff = self.compare_labels(true_labels, pred_labels)
            total_labels = len(true_labels)
            error_rate = (len(mismatches) / total_labels) * 100 if total_labels > 0 else 0

            results[filename] = {
                'total_labels': total_labels,
                'mismatches': len(mismatches),
                'length_diff': length_diff,
                'error_rate': error_rate,
                'mismatch_indices': mismatches,
                'true_path': true_path,
                'pred_path': pred_path,
                'true_filename': os.path.basename(true_path),
                'pred_filename': os.path.basename(pred_path)
            }

            self.file_processed.emit(filename)
            progress = int((i + 1) / total_files * 100)
            self.progress.emit(progress)

        return results


class StatisticsPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            StatisticsPanel {
                background-color: white;
                border: 1.5px solid #E0E0E0;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout(self)
        layout.setHorizontalSpacing(20)

        stats = [
            ("📊", "文件总数", "total_files", "0"),
            ("🔢", "总标签数", "total_labels", "0"),
            ("❌", "不匹配数", "mismatches", "0"),
            ("📈", "错误率", "error_rate", "0%")
        ]

        for i, (icon, title, obj_name, value) in enumerate(stats):
            stat_widget = self.create_stat_widget(icon, title, value)
            layout.addWidget(stat_widget, 0, i)
            # 找到value_label并设置属性
            value_label = stat_widget.findChild(QLabel, "value")
            setattr(self, obj_name, value_label)

    def create_stat_widget(self, icon, title, value):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        icon_label = QLabel(icon)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666666; font-size: 12px;")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()

        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #333333;")

        layout.addLayout(header)
        layout.addWidget(value_label)

        return widget

    def update_stats(self, results):
        if not results:
            return

        total_files = len(results)
        total_labels = sum(data['total_labels'] for data in results.values())
        total_mismatches = sum(data['mismatches'] for data in results.values())
        overall_error_rate = (total_mismatches / total_labels) * 100 if total_labels > 0 else 0

        self.total_files.setText(str(total_files))
        self.total_labels.setText(str(total_labels))
        self.mismatches.setText(str(total_mismatches))
        self.error_rate.setText(f"{overall_error_rate:.1f}%")


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")
        self.setFixedSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("使用说明")
        title.setStyleSheet("font-size: 18px; font-weight: 700; padding: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setPlainText("""
🎯 核心功能

• 智能比较SEG文件标签差异
• 自动按错误率分类文件
• 可视化显示比较结果
• 批量复制分类文件

🚀 使用步骤

1. 设置参考目录和预测目录
2. 点击开始比较按钮
3. 查看比较结果
4. 选择分类进行文件操作

📊 错误分类

• 完美匹配(0%)
• 极轻微错误(0-1%)
• 轻微错误(1-3%)
• 中等错误(3-10%)
• 严重错误(10%+)
• 长度不一致
        """)
        layout.addWidget(content)

        ok_btn = ModernButton("确定", primary=True)
        ok_btn.set_style("#0084FF")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


class SegComparisonTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SEG文件比较工具")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)

        self.true_dir = ""
        self.pred_dir = ""
        self.results = {}
        self.categories = {}

        self.setup_styles()
        self.init_ui()

    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QTabWidget::pane {
                border: none;
                background-color: white;
            }
            QTabBar::tab {
                background-color: transparent;
                border: none;
                padding: 12px 20px;
                font-size: 13px;
                color: #666666;
            }
            QTabBar::tab:selected {
                color: #0084FF;
                font-weight: 600;
                border-bottom: 2px solid #0084FF;
            }
            QTreeWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #F8F8F8;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                font-weight: 600;
            }
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px;
                font-family: monospace;
            }
        """)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 侧边栏
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.create_toolbar(content_layout)
        self.create_content_area(content_layout)

        main_layout.addWidget(content_widget, 1)

        self.statusBar().showMessage("就绪")

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #F8F8F8; border-right: 1px solid #E0E0E0;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 16, 8, 16)

        title = QLabel("SEG比较工具")
        title.setStyleSheet("font-size: 16px; font-weight: 600; padding: 8px 12px;")
        layout.addWidget(title)

        self.comparison_btn = SidebarButton("🔍 文件比较")
        self.comparison_btn.setChecked(True)
        self.comparison_btn.clicked.connect(lambda: self.switch_tab("comparison"))

        self.results_btn = SidebarButton("📊 比较结果")
        self.results_btn.clicked.connect(lambda: self.switch_tab("results"))

        self.operations_btn = SidebarButton("🛠️ 文件操作")
        self.operations_btn.clicked.connect(lambda: self.switch_tab("operations"))

        layout.addWidget(self.comparison_btn)
        layout.addWidget(self.results_btn)
        layout.addWidget(self.operations_btn)
        layout.addStretch()

        help_btn = SidebarButton("❓ 使用说明")
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)

        return sidebar

    def create_toolbar(self, parent_layout):
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setStyleSheet("background-color: white; border-bottom: 1px solid #E0E0E0;")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(24, 12, 24, 12)

        self.toolbar_title = QLabel("文件比较")
        self.toolbar_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(self.toolbar_title)
        layout.addStretch()

        clear_btn = ModernButton("清空结果")
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)

        parent_layout.addWidget(toolbar)

    def create_content_area(self, parent_layout):
        self.stacked_widget = QWidget()
        self.stacked_layout = QVBoxLayout(self.stacked_widget)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)

        self.create_comparison_tab()
        self.create_results_tab()
        self.create_operations_tab()

        parent_layout.addWidget(self.stacked_widget, 1)

    def create_comparison_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 目录设置
        dir_card = QFrame()
        dir_card.setStyleSheet("background-color: white; border: 1px solid #E0E0E0; border-radius: 8px;")
        dir_layout = QVBoxLayout(dir_card)

        card_title = QLabel("目录设置")
        card_title.setStyleSheet("font-weight: 600; padding: 16px; border-bottom: 1px solid #F0F0F0;")
        dir_layout.addWidget(card_title)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(16, 16, 16, 16)

        # 参考目录
        ref_layout = QVBoxLayout()
        ref_layout.addWidget(QLabel("参考目录"))
        self.true_dir_input = DirectoryInput("选择参考标签目录...")
        self.true_dir_input.browse_btn.clicked.connect(self.browse_true_dir)
        ref_layout.addWidget(self.true_dir_input)
        content_layout.addLayout(ref_layout)

        # 预测目录
        pred_layout = QVBoxLayout()
        pred_layout.addWidget(QLabel("预测目录"))
        self.pred_dir_input = DirectoryInput("选择预测标签目录...")
        self.pred_dir_input.browse_btn.clicked.connect(self.browse_pred_dir)
        pred_layout.addWidget(self.pred_dir_input)
        content_layout.addLayout(pred_layout)

        dir_layout.addWidget(content)
        layout.addWidget(dir_card)

        # 比较按钮
        self.compare_btn = ModernButton("开始比较SEG文件", primary=True)
        self.compare_btn.set_style("#0084FF")
        self.compare_btn.clicked.connect(self.compare_seg_files)
        layout.addWidget(self.compare_btn)

        # 进度区域
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.current_file_label = QLabel("就绪")
        self.current_file_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.current_file_label)

        layout.addStretch()

        self.comparison_tab = widget
        self.stacked_layout.addWidget(widget)

    def create_results_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        self.stats_panel = StatisticsPanel()
        layout.addWidget(self.stats_panel)

        self.tab_widget = QTabWidget()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.tab_widget.addTab(self.summary_text, "汇总统计")

        self.details_tree = QTreeWidget()
        self.details_tree.setHeaderLabels(["参考文件", "预测文件", "总标签数", "不匹配数", "长度差异", "错误率", "状态"])
        self.details_tree.itemDoubleClicked.connect(self.show_mismatch_details)
        self.tab_widget.addTab(self.details_tree, "详细结果")

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabels(["错误分类", "文件数量", "总标签数", "总不匹配数", "平均错误率"])
        self.category_tree.itemDoubleClicked.connect(self.show_category_files)
        self.tab_widget.addTab(self.category_tree, "分类分析")

        layout.addWidget(self.tab_widget, 1)

        self.results_tab = widget
        self.results_tab.setVisible(False)
        self.stacked_layout.addWidget(widget)

    def create_operations_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        op_card = QFrame()
        op_card.setStyleSheet("background-color: white; border: 1px solid #E0E0E0; border-radius: 8px; padding: 20px;")
        op_layout = QVBoxLayout(op_card)
        op_layout.setSpacing(16)

        # 文件来源
        source_label = QLabel("复制文件来源")
        source_label.setStyleSheet("font-weight: 600;")
        op_layout.addWidget(source_label)

        radio_layout = QHBoxLayout()
        self.source_radio_ref = QRadioButton("仅参考文件")
        self.source_radio_pred = QRadioButton("仅预测文件")
        self.source_radio_both = QRadioButton("两者都复制")
        self.source_radio_both.setChecked(True)
        radio_layout.addWidget(self.source_radio_ref)
        radio_layout.addWidget(self.source_radio_pred)
        radio_layout.addWidget(self.source_radio_both)
        radio_layout.addStretch()
        op_layout.addLayout(radio_layout)

        # 分类选择
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("选择分类"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "完美匹配(0%)", "极轻微错误(0-1%)", "轻微错误(1-3%)",
            "中等偏轻错误(3-5%)", "中等错误(5-10%)", "中等偏重错误(10-15%)",
            "显著错误(15-20%)", "严重错误(20-30%)", "非常严重错误(30-50%)",
            "极端严重错误(>50%)", "长度不一致"
        ])
        category_layout.addWidget(self.category_combo, 1)
        op_layout.addLayout(category_layout)

        # 目标目录
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("目标目录"))
        self.target_dir_input = DirectoryInput("选择文件复制目标目录...")
        self.target_dir_input.browse_btn.clicked.connect(self.browse_target_dir)
        target_layout.addWidget(self.target_dir_input, 1)
        op_layout.addLayout(target_layout)

        layout.addWidget(op_card)

        copy_btn = ModernButton("复制选定文件", primary=True)
        copy_btn.set_style("#0084FF")
        copy_btn.clicked.connect(self.copy_selected_files)
        layout.addWidget(copy_btn)
        layout.addStretch()

        self.operations_tab = widget
        self.operations_tab.setVisible(False)
        self.stacked_layout.addWidget(widget)

    def switch_tab(self, tab_name):
        self.comparison_tab.setVisible(tab_name == "comparison")
        self.results_tab.setVisible(tab_name == "results")
        self.operations_tab.setVisible(tab_name == "operations")

        titles = {
            "comparison": "文件比较",
            "results": "比较结果",
            "operations": "文件操作"
        }
        self.toolbar_title.setText(titles.get(tab_name, "文件比较"))

        self.comparison_btn.setChecked(tab_name == "comparison")
        self.results_btn.setChecked(tab_name == "results")
        self.operations_btn.setChecked(tab_name == "operations")

    def clear_results(self):
        self.results.clear()
        self.categories.clear()
        self.summary_text.clear()
        self.details_tree.clear()
        self.category_tree.clear()
        self.stats_panel.update_stats({})
        self.statusBar().showMessage("结果已清空")

    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def browse_true_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择参考标签目录")
        if dir_path:
            self.true_dir_input.setText(dir_path)

    def browse_pred_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择预测标签目录")
        if dir_path:
            self.pred_dir_input.setText(dir_path)

    def browse_target_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if dir_path:
            self.target_dir_input.setText(dir_path)

    def compare_seg_files(self):
        true_dir = self.true_dir_input.text()
        pred_dir = self.pred_dir_input.text()

        if not true_dir or not os.path.isdir(true_dir):
            QMessageBox.warning(self, "错误", "请选择有效的参考标签目录")
            return

        if not pred_dir or not os.path.isdir(pred_dir):
            QMessageBox.warning(self, "错误", "请选择有效的预测标签目录")
            return

        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.current_file_label.setText("开始比较...")

        self.worker = ComparisonWorker(true_dir, pred_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        self.worker.file_processed.connect(self.on_file_processed)
        self.worker.start()

    def on_file_processed(self, filename):
        self.current_file_label.setText(f"正在处理: {filename}")

    def on_comparison_finished(self, results):
        self.results = results
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_file_label.setText("比较完成")

        if self.results:
            self.display_results()
            self.stats_panel.update_stats(self.results)
            self.switch_tab("results")
            QMessageBox.information(self, "完成", f"比较完成！共处理 {len(self.results)} 个文件")

    def on_comparison_error(self, error_message):
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.current_file_label.setText("比较出错")
        QMessageBox.warning(self, "错误", error_message)

    def display_results(self):
        self.summary_text.clear()
        self.details_tree.clear()
        self.category_tree.clear()

        total_files = len(self.results)
        total_labels = sum(data['total_labels'] for data in self.results.values())
        total_mismatches = sum(data['mismatches'] for data in self.results.values())
        total_diff = sum(data['length_diff'] for data in self.results.values())
        overall_error_rate = (total_mismatches / total_labels) * 100 if total_labels > 0 else 0

        summary_text = f"""SEG文件标签对比结果

📊 比较文件总数: {total_files}
🔢 总标签数: {total_labels}
❌ 总不匹配标签数: {total_mismatches}
📏 总长度差异: {total_diff}
📈 总体错误率: {overall_error_rate:.2f}%

"""
        self.summary_text.setPlainText(summary_text)

        for filename, data in self.results.items():
            status_icon = "✅" if data['error_rate'] == 0 else "⚠️" if data['error_rate'] < 5 else "❌"
            item = QTreeWidgetItem([
                data['true_filename'],
                data['pred_filename'],
                str(data['total_labels']),
                str(data['mismatches']),
                str(data['length_diff']),
                f"{data['error_rate']:.2f}%",
                status_icon
            ])
            self.set_error_rate_color(item, data['error_rate'])
            self.details_tree.addTopLevelItem(item)

        self.categorize_results()
        for category, data in self.categories.items():
            if data["count"] > 0:
                avg_error = (data["total_mismatches"] / data["total_labels"]) * 100 if data["total_labels"] > 0 else 0
                item = QTreeWidgetItem([
                    category,
                    str(data["count"]),
                    str(data["total_labels"]),
                    str(data["total_mismatches"]),
                    f"{avg_error:.2f}%"
                ])
                self.set_category_color(item, category)
                self.category_tree.addTopLevelItem(item)

    def set_error_rate_color(self, item, error_rate):
        color_cols = [3, 4, 5]
        for col in color_cols:
            if error_rate > 50:
                item.setForeground(col, QBrush(QColor(220, 53, 69)))
            elif error_rate > 30:
                item.setForeground(col, QBrush(QColor(255, 99, 132)))
            elif error_rate > 20:
                item.setForeground(col, QBrush(QColor(255, 159, 67)))
            elif error_rate > 10:
                item.setForeground(col, QBrush(QColor(255, 205, 86)))
            elif error_rate > 5:
                item.setForeground(col, QBrush(QColor(72, 187, 120)))
            elif error_rate > 0:
                item.setForeground(col, QBrush(QColor(54, 162, 235)))

    def set_category_color(self, item, category):
        if "极端" in category:
            item.setForeground(0, QBrush(QColor(220, 53, 69)))
        elif "非常严重" in category:
            item.setForeground(0, QBrush(QColor(255, 99, 132)))
        elif "严重" in category:
            item.setForeground(0, QBrush(QColor(255, 159, 67)))
        elif "显著" in category:
            item.setForeground(0, QBrush(QColor(255, 205, 86)))
        elif "中等" in category:
            item.setForeground(0, QBrush(QColor(72, 187, 120)))
        elif "轻微" in category:
            item.setForeground(0, QBrush(QColor(54, 162, 235)))
        elif "完美" in category:
            item.setForeground(0, QBrush(QColor(40, 167, 69)))
        elif "长度" in category:
            item.setForeground(0, QBrush(QColor(111, 66, 193)))

    def categorize_results(self):
        self.categories = {
            "完美匹配(0%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "极轻微错误(0-1%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "轻微错误(1-3%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "中等偏轻错误(3-5%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "中等错误(5-10%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "中等偏重错误(10-15%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "显著错误(15-20%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "严重错误(20-30%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "非常严重错误(30-50%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "极端严重错误(>50%)": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []},
            "长度不一致": {"count": 0, "total_labels": 0, "total_mismatches": 0, "files": []}
        }

        for filename, data in self.results.items():
            if data['length_diff'] > 0:
                category = "长度不一致"
            elif data['error_rate'] == 0:
                category = "完美匹配(0%)"
            elif data['error_rate'] <= 1:
                category = "极轻微错误(0-1%)"
            elif data['error_rate'] <= 3:
                category = "轻微错误(1-3%)"
            elif data['error_rate'] <= 5:
                category = "中等偏轻错误(3-5%)"
            elif data['error_rate'] <= 10:
                category = "中等错误(5-10%)"
            elif data['error_rate'] <= 15:
                category = "中等偏重错误(10-15%)"
            elif data['error_rate'] <= 20:
                category = "显著错误(15-20%)"
            elif data['error_rate'] <= 30:
                category = "严重错误(20-30%)"
            elif data['error_rate'] <= 50:
                category = "非常严重错误(30-50%)"
            else:
                category = "极端严重错误(>50%)"

            self.categories[category]["count"] += 1
            self.categories[category]["total_labels"] += data['total_labels']
            self.categories[category]["total_mismatches"] += data['mismatches']
            self.categories[category]["files"].append(filename)

    def show_mismatch_details(self, item, column):
        filename = item.text(0)
        for key, data in self.results.items():
            if data['true_filename'] == filename:
                details = f"""文件比较详情

参考文件: {data['true_filename']}
预测文件: {data['pred_filename']}

总标签数: {data['total_labels']}
不匹配标签数: {data['mismatches']}
长度差异: {data['length_diff']}
错误率: {data['error_rate']:.2f}%

"""
                if data['mismatch_indices']:
                    details += f"前10个不匹配位置: {data['mismatch_indices'][:10]}"
                    if len(data['mismatch_indices']) > 10:
                        details += f" ... (共{len(data['mismatch_indices'])}个)"
                else:
                    details += "没有不匹配的标签"

                QMessageBox.information(self, "文件比较详情", details)
                break

    def show_category_files(self, item, column):
        category = item.text(0)
        files = self.categories.get(category, {}).get("files", [])
        if not files:
            return
        file_list = "\n".join(files)
        QMessageBox.information(self, f"{category}", f"该分类共有 {len(files)} 个文件:\n\n{file_list}")

    def copy_selected_files(self):
        target_dir = self.target_dir_input.text()
        if not target_dir or not os.path.isdir(target_dir):
            QMessageBox.warning(self, "错误", "请选择有效的目标目录")
            return

        category = self.category_combo.currentText()
        files = self.categories.get(category, {}).get("files", [])
        if not files:
            QMessageBox.information(self, "提示", f"没有找到属于'{category}'分类的文件")
            return

        category_dir = os.path.join(target_dir, category.replace('/', '_'))
        os.makedirs(category_dir, exist_ok=True)

        ref_dir = os.path.join(category_dir, "ref")
        pred_dir = os.path.join(category_dir, "pred")
        if self.source_radio_ref.isChecked() or self.source_radio_both.isChecked():
            os.makedirs(ref_dir, exist_ok=True)
        if self.source_radio_pred.isChecked() or self.source_radio_both.isChecked():
            os.makedirs(pred_dir, exist_ok=True)

        copied_ref_count = 0
        copied_pred_count = 0

        for filename in files:
            try:
                if self.source_radio_ref.isChecked() or self.source_radio_both.isChecked():
                    src_path = self.results[filename]['true_path']
                    dst_path = os.path.join(ref_dir, filename)
                    shutil.copy2(src_path, dst_path)
                    copied_ref_count += 1

                if self.source_radio_pred.isChecked() or self.source_radio_both.isChecked():
                    src_path = self.results[filename]['pred_path']
                    dst_path = os.path.join(pred_dir, filename)
                    shutil.copy2(src_path, dst_path)
                    copied_pred_count += 1
            except Exception as e:
                print(f"复制文件 {filename} 时出错: {e}")

        message = f"""文件复制完成！

目标位置: {category_dir}
分类: {category}

"""
        if self.source_radio_ref.isChecked() or self.source_radio_both.isChecked():
            message += f"参考文件 → ref/ 目录 ({copied_ref_count}个)\n"
        if self.source_radio_pred.isChecked() or self.source_radio_both.isChecked():
            message += f"预测文件 → pred/ 目录 ({copied_pred_count}个)\n"
        message += f"\n总计复制: {copied_ref_count + copied_pred_count} 个文件"

        QMessageBox.information(self, "复制完成", message)


if __name__ == "__main__":
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    window = SegComparisonTool()
    window.show()
    sys.exit(app.exec_())