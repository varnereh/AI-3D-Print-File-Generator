
import sys
import os
import platform
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QPushButton, QTextEdit, QLabel, QSplitter, 
                             QFrame, QFileDialog, QListWidgetItem, QScrollArea, QTreeView,
                             QMenu, QAction, QMenuBar, QFileSystemModel, QTabWidget, QPlainTextEdit,
                             QInputDialog, QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QSize, QDir, QProcess, QPoint, QModelIndex
from PyQt5.QtGui import QIcon, QFont
    
from PyQt5.QtWidgets import QInputDialog
from gradio_client import Client, handle_file, FileData
import pyqtgraph.opengl as gl
import numpy as np
import trimesh

class ThreeDImageGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Image Generator")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QListWidget, QTreeView {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLabel {
                font-weight: bold;
                color: #333333;
            }
            QFrame {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QMenuBar {
                background-color: #f8f8f8;
                border-bottom: 1px solid #cccccc;
            }
            QMenuBar::item {
                padding: 6px 10px;
                spacing: 5px;
            }
            QMenuBar::item:selected {
                background: #e0e0e0;
                border-radius: 3px;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #cccccc;
                border-bottom-color: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom-color: #ffffff;
            }
        """)
        self.batch_size = 4
        self.guidance_scale = 7.5

        # Create menu bar
        self.create_menu_bar()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create tabbed interface for left panel
        self.tabs = QTabWidget()
        
        # Create File Explorer tab
        file_explorer_widget = QWidget()
        file_explorer_layout = QVBoxLayout(file_explorer_widget)
        
        # Set up file system model and view
        self.file_model = QFileSystemModel()
        # self.file_model.setRootPath(QDir.homePath())
        last_folder = self.load_last_folder()
        self.current_directory = last_folder
        index = self.file_model.setRootPath(last_folder)  # capture the returned index
        self.file_model.setNameFilters(["*.obj", "*.stl", "*.3d"])
        self.file_model.setNameFilterDisables(False)  # Hide non-matching files
        self.file_model.setReadOnly(False)            # Allow rename, drag/drop moves
        
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        # self.file_tree.setRootIndex(self.file_model.index(QDir.homePath()))
        self.file_tree.setRootIndex(index)  # use the returned index

        # Enable drag & drop move and inline rename
        self.file_tree.setDragEnabled(True)
        self.file_tree.setAcceptDrops(True)
        self.file_tree.setDropIndicatorShown(True)
        self.file_tree.setDefaultDropAction(Qt.MoveAction)
        self.file_tree.setDragDropMode(QTreeView.DragDrop)
        self.file_tree.setEditTriggers(QTreeView.EditKeyPressed | QTreeView.SelectedClicked)

        self.file_tree.setAnimated(True)
        self.file_tree.setIndentation(20)
        self.file_tree.setSortingEnabled(True)
        self.file_tree.setColumnWidth(0, 200)  # Adjust the width of the first column
        
        # Hide unnecessary columns (size, type, date modified)
        for i in range(1, 4):
            self.file_tree.hideColumn(i)
        
        self.file_tree.clicked.connect(self.on_file_clicked)
        
        # Context menu
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._show_fs_context_menu)

        # Keyboard shortcuts (Copy, Cut, Paste, Delete, Rename, New Folder)
        self._init_fs_shortcuts()

        file_explorer_layout.addWidget(QLabel("File Explorer"))
        file_explorer_layout.addWidget(self.file_tree)
        
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        # self.save_button.clicked.connect(self.save_object)
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_object)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.export_button)
        
        # Add tabs to the tabbed interface
        self.tabs.addTab(file_explorer_widget, "Files")
        
        # Add tabs to left layout
        left_layout.addWidget(self.tabs)
        
        # Create right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 3D view section
        view_label = QLabel("3D Object View")
        self.view_widget = gl.GLViewWidget()
        self.view_widget.setMinimumHeight(400)
        self.view_widget.setCameraPosition(distance=40)
        
        # Add grid for reference
        grid = gl.GLGridItem()
        grid.setSize(x=20, y=20, z=0)
        grid.setSpacing(x=1, y=1, z=1)
        self.view_widget.addItem(grid)
        
        # Add axes for reference
        axes = gl.GLAxisItem()
        axes.setSize(x=5, y=5, z=5)
        self.view_widget.addItem(axes)
        
        # Chat section
        chat_label = QLabel("AI Conversation")
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Describe the 3D image you want to generate...")
        self.chat_input.setMaximumHeight(80)

        # Image upload button
        self.image_button = QPushButton("Create 3D Model from Image")
        self.image_button.clicked.connect(self.select_image_for_generation)
        
        # Store the selected image path
        self.selected_image_path = None
        
        self.send_button = QPushButton("Generate")
        self.send_button.clicked.connect(self.generate_3d_object)
        
        # Splitter for view, chat history, and input
        vertical_splitter = QSplitter(Qt.Vertical)

        # Top: 3D View
        view_container = QWidget()
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_label.setParent(None)  # Prevent duplication if it was added earlier
        view_layout.addWidget(view_label)
        view_layout.addWidget(self.view_widget)
        view_container.setMinimumHeight(150)

        # Middle: Chat History
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_label.setParent(None)
        chat_layout.addWidget(chat_label)
        chat_layout.addWidget(self.chat_history)
        chat_container.setMinimumHeight(100)

        # Bottom: Input + Send Button
        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Text input row
        text_input_row = QHBoxLayout()
        self.chat_input.setMinimumHeight(40)
        self.send_button.setMinimumHeight(40)
        text_input_row.addWidget(self.chat_input)
        text_input_row.addWidget(self.send_button)
        
        # Image button row
        image_button_row = QHBoxLayout()
        self.image_button.setMinimumHeight(40)
        image_button_row.addWidget(self.image_button)
        
        input_layout.addLayout(text_input_row)
        input_layout.addLayout(image_button_row)
        input_container.setMinimumHeight(100)

        # Add widgets to vertical splitter
        vertical_splitter.addWidget(view_container)
        vertical_splitter.addWidget(chat_container)
        vertical_splitter.addWidget(input_container)

        # Stretch factors to guide resize behavior
        vertical_splitter.setStretchFactor(0, 3)  # 3D view
        vertical_splitter.setStretchFactor(1, 2)  # Chat history
        vertical_splitter.setStretchFactor(2, 1)  # Input

        # Add the splitter to the right layout
        right_layout.addWidget(vertical_splitter)
        
        # Create splitter to allow resizing
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setSizes([300, 900])  # Initial sizes
        
        main_layout.addWidget(self.main_splitter)
        
        
        # Initialize current directory
        self.current_directory = QDir.homePath()
        # self.current_directory = os.path.join(self.current_directory, "Objects")
        
        # Dictionary to store loaded meshes for reference
        self.loaded_meshes = {}
        
        # Clipboard for copy/cut
        self._clipboard_paths = []   # list[str]
        self._clipboard_mode  = None # 'copy' or 'cut'

        # setting default mode to turbo for fastest model mode as default
        # if this is not called, then the model does not have settings to begin with
        self.set_hunyuan3d_mode("turbo")

        self.show()
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Open folder action
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)
        
        # Create new folder action
        new_folder_action = QAction("New Folder", self)
        new_folder_action.triggered.connect(self.create_new_folder)
        file_menu.addAction(new_folder_action)
        
        file_menu.addSeparator()
        
        # Import object action
        import_action = QAction("Import Object", self)
        import_action.triggered.connect(self.import_object)
        file_menu.addAction(import_action)
        
        # Export object action
        export_action = QAction("Export Object", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self.export_object)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("View")
        
        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_file_view)
        view_menu.addAction(refresh_action)
        
        # Show hidden files action
        hidden_files_action = QAction("Show Hidden Files", self)
        hidden_files_action.setCheckable(True)
        hidden_files_action.triggered.connect(self.toggle_hidden_files)
        view_menu.addAction(hidden_files_action)

        # Advanced Settings menu
        advanced_menu = menu_bar.addMenu("Advanced Settings")

        # Preset options
        turbo_action = QAction("Turbo", self)
        turbo_action.triggered.connect(lambda: self.set_hunyuan3d_mode("turbo"))
        advanced_menu.addAction(turbo_action)

        fast_action = QAction("Fast", self)
        fast_action.triggered.connect(lambda: self.set_hunyuan3d_mode("fast"))
        advanced_menu.addAction(fast_action)

        standard_action = QAction("Standard", self)
        standard_action.triggered.connect(lambda: self.set_hunyuan3d_mode("standard"))
        advanced_menu.addAction(standard_action)

        advanced_menu.addSeparator()

        custom_action = QAction("Custom Settings...", self)
        custom_action.triggered.connect(self.custom_hunyuan3d_dialog)
        advanced_menu.addAction(custom_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)


    def set_hunyuan3d_mode(self, mode):
        """
        Set internal parameters to match Hunyuan3D 2.0 “Turbo / Fast / Standard” presets.
        You’ll need to decide the numeric values based on your experimentation.
        """
        if mode == "turbo":
            # These are example values; you should adjust them
            self.num_inference_steps = 20
            self.guidance_scale = 5.0
            self.face_count = 50000
            self.octree_resolution = 64
        elif mode == "fast":
            self.num_inference_steps = 40
            self.guidance_scale = 7.5
            self.face_count = 100000
            self.octree_resolution = 128
        elif mode == "standard":
            self.num_inference_steps = 80
            self.guidance_scale = 12.0
            self.face_count = 200000
            self.octree_resolution = 256

        # Log or display the chosen settings
        self.chat_history.append(
            f"<b>System:</b> Hunyuan3D mode set to <b>{mode.capitalize()}</b> "
            f"(Steps: {self.num_inference_steps}, Guidance: {self.guidance_scale}, "
            f"Faces: {self.face_count}, Octree: {self.octree_resolution})"
        )


    def custom_hunyuan3d_dialog(self):
        """
        Show a single dialog to collect all custom settings at once,
        then apply them if the user clicks OK.
        """
        # Use current values if present; otherwise fall back to your previous defaults
        steps_default = getattr(self, "num_inference_steps", 80)
        guidance_default = getattr(self, "guidance_scale", 7.5)
        faces_default = getattr(self, "face_count", 100000)
        octree_default = getattr(self, "octree_resolution", 128)

        dlg = CustomSettingsDialog(
            self,
            steps=steps_default,
            guidance=guidance_default,
            faces=faces_default,
            octree=octree_default,
        )

        if dlg.exec_() == QDialog.Accepted:
            steps, guidance, faces, octree = dlg.values()
            # Apply custom values
            self.num_inference_steps = steps
            self.guidance_scale = guidance
            self.face_count = faces
            self.octree_resolution = octree

            self.chat_history.append(
                f"<b>System:</b> Custom Hunyuan3D settings set "
                f"(Steps: {steps}, Guidance: {guidance}, Faces: {faces}, Octree: {octree})"
            )




    # ---- Context Menu + FS Helper Functions ---- 
    # These functions help manage the file system view and context menu actions
    def _init_fs_shortcuts(self):
        # Copy
        act_copy = QAction("Copy", self)
        act_copy.setShortcut("Ctrl+C" if platform.system() != "Darwin" else "Meta+C")
        act_copy.triggered.connect(lambda: self._fs_copy_or_cut(mode="copy"))
        self.addAction(act_copy)

        # Cut
        act_cut = QAction("Cut", self)
        act_cut.setShortcut("Ctrl+X" if platform.system() != "Darwin" else "Meta+X")
        act_cut.triggered.connect(lambda: self._fs_copy_or_cut(mode="cut"))
        self.addAction(act_cut)

        # Paste
        act_paste = QAction("Paste", self)
        act_paste.setShortcut("Ctrl+V" if platform.system() != "Darwin" else "Meta+V")
        act_paste.triggered.connect(lambda checked=False: self._fs_paste())
        self.addAction(act_paste)

        # Delete (permanent)
        act_delete = QAction("Delete", self)
        act_delete.setShortcut("Del")
        act_delete.triggered.connect(lambda checked=False: self._fs_delete())
        self.addAction(act_delete)

        # Rename (inline)
        act_rename = QAction("Rename", self)
        act_rename.setShortcut("F2")
        act_rename.triggered.connect(lambda checked=False: self._fs_rename())
        self.addAction(act_rename)

        # New Folder
        act_new_folder = QAction("New Folder", self)
        if platform.system() == "Darwin":
            act_new_folder.setShortcut("Meta+Shift+N")
        else:
            act_new_folder.setShortcut("Ctrl+Shift+N")
        act_new_folder.triggered.connect(lambda checked=False: self._fs_new_folder())
        self.addAction(act_new_folder)

    # Context menu event
    def _show_fs_context_menu(self, pos: QPoint):
        index = self.file_tree.indexAt(pos)
        global_pos = self.file_tree.viewport().mapToGlobal(pos)

        menu = QMenu(self)

        is_valid = index.isValid()
        is_dir = self.file_model.isDir(index) if is_valid else True

        # Common actions
        act_open_in_os = QAction("Reveal in File Explorer" if platform.system() == "Windows" else "Reveal in Finder", self)
        act_open_in_os.triggered.connect(lambda: self._fs_reveal(index))
        act_copy  = QAction("Copy", self)
        act_cut   = QAction("Cut", self)
        act_paste = QAction("Paste", self)
        act_del   = QAction("Delete", self)
        act_ren   = QAction("Rename", self)
        act_new   = QAction("New Folder", self)

        act_copy.triggered.connect(lambda: self._fs_copy_or_cut(mode="copy", index=index))
        act_cut.triggered.connect(lambda: self._fs_copy_or_cut(mode="cut", index=index))
        act_paste.triggered.connect(lambda: self._fs_paste(index=index))
        act_del.triggered.connect(lambda: self._fs_delete(index=index))
        act_ren.triggered.connect(lambda: self._fs_rename(index=index))
        act_new.triggered.connect(lambda: self._fs_new_folder(index=index if is_dir else index.parent()))

        if is_valid:
            menu.addAction(act_open_in_os)
            menu.addSeparator()
            menu.addAction(act_copy)
            menu.addAction(act_cut)
            menu.addAction(act_paste)
            menu.addSeparator()
            menu.addAction(act_ren)
            menu.addAction(act_del)
            if is_dir:
                menu.addSeparator()
                menu.addAction(act_new)
        else:
            # clicked empty area and allow paste/new in root
            menu.addAction(act_paste)
            menu.addAction(act_new)

        menu.exec_(global_pos)

    # Helper to get selected indexes (column 0 only)
    def _selected_indexes(self):
        """Return selected model indexes (column 0 only)."""
        idxs = [i for i in self.file_tree.selectedIndexes() if i.column() == 0]
        return idxs

    # Get file paths from indexes
    def _paths_from_indexes(self, indexes):
        paths = []
        for i in indexes:
            p = self.file_model.filePath(i)
            if p:
                paths.append(p)
        return paths

    # Copy/Cut clipboard state
    def _fs_copy_or_cut(self, mode: str, index: QModelIndex = None):
        """Copy/Cut selected files/folders to clipboard."""
        if index is None:
            idxs = self._selected_indexes()
        else:
            idxs = [index]
        if not idxs:
            return
        self._clipboard_paths = self._paths_from_indexes(idxs)
        self._clipboard_mode = mode
        self.chat_history.append(f"<b>System:</b> {mode.capitalize()} {len(self._clipboard_paths)} item(s).")

    # Paste directory from clipboard
    def _paste_target_dir(self, index: QModelIndex = None):
        """
        Decide where to paste: If a folder is selected, paste into it.
        If a file is selected, paste into its parent. If no index was provided 
        (e.g., keyboard shortcut), use the current selection,
        then currentIndex(), and only then fall back to the tree root.
        """
        # normalize QAction.triggered(bool) -> None
        if isinstance(index, bool):
            index = None

        # If no explicit index, use the selection
        if index is None or not index.isValid():
            sel = self._selected_indexes()
            if sel:
                index = sel[0]

        # If still nothing, use the current tree index
        if index is None or not index.isValid():
            cur = self.file_tree.currentIndex()
            if cur.isValid():
                index = cur

        # If still don't have a valid index, fall back to the root
        if index is None or not index.isValid():
            return self.file_model.filePath(self.file_tree.rootIndex())

        # If a folder is selected, paste into it; if a file, paste into its parent
        if self.file_model.isDir(index):
            return self.file_model.filePath(index)
        else:
            parent = index.parent()
            return self.file_model.filePath(parent)

    # Setting path for copied items
    def _unique_dest_path(self, dst_dir: str, name: str) -> str:
        """Avoid overwriting: add ' copy', ' copy (2)', ..."""
        base, ext = os.path.splitext(name)
        candidate = os.path.join(dst_dir, name)
        n = 1
        while os.path.exists(candidate):
            suffix = f" copy" if n == 1 else f" copy ({n})"
            candidate = os.path.join(dst_dir, f"{base}{suffix}{ext}")
            n += 1
        return candidate

    # Copy item (file or folder)
    def _copy_item(self, src: str, dst_dir: str):
        name = os.path.basename(src)
        dst = self._unique_dest_path(dst_dir, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # Move item (file or folder)
    def _move_item(self, src: str, dst_dir: str):
        name = os.path.basename(src)
        dst = os.path.join(dst_dir, name)
        if os.path.abspath(os.path.dirname(src)) == os.path.abspath(dst_dir):
            # moving within same folder: treat like rename 
            dst = self._unique_dest_path(dst_dir, name)
        shutil.move(src, dst)

    # Delete item (file or folder)
    def _fs_paste(self, index: QModelIndex = None):
        if isinstance(index, bool):
            index = None
        if not self._clipboard_paths or self._clipboard_mode not in ("copy", "cut"):
            return
        dst_dir = self._paste_target_dir(index)
        if not os.path.isdir(dst_dir):
            return

        # Paste what the user chose; folders always ok.
        for src in self._clipboard_paths:
            try:
                if self._clipboard_mode == "copy":
                    self._copy_item(src, dst_dir)
                else:
                    self._move_item(src, dst_dir)
            except Exception as e:
                self.chat_history.append(f"<b>Error:</b> Paste failed for {os.path.basename(src)} — {e}")

        # if it was a cut, clear clipboard
        if self._clipboard_mode == "cut":
            self._clipboard_paths = []
            self._clipboard_mode = None

        self.refresh_file_view()

    # Delete item (file or folder)
    def _fs_delete(self, index: QModelIndex = None):
        if isinstance(index, bool):
            index = None
        idxs = [index] if (index is not None and index.isValid()) else self._selected_indexes()
        if not idxs:
            return
        paths = self._paths_from_indexes(idxs)
        for p in paths:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                self.chat_history.append(f"<b>Error:</b> Delete failed for {os.path.basename(p)} — {e}")
        self.refresh_file_view()

    # Rename item (inline)
    def _fs_rename(self, index: QModelIndex = None):
        if isinstance(index, bool):
            index = None
        """Start inline rename on the given or selected index (column 0)."""
        if index is None or not index.isValid():
            idxs = self._selected_indexes()
            if not idxs:
                return
            index = idxs[0]
        # ensure first column
        index = index.sibling(index.row(), 0)
        self.file_tree.edit(index)  # inline editor

    # Create new folder
    def _fs_new_folder(self, index: QModelIndex = None):
        if isinstance(index, bool):
            index = None
        # Determine parent dir for the new folder
        if index is None or not index.isValid():
            parent_dir = self.file_model.filePath(self.file_tree.rootIndex())
            parent_index = self.file_tree.rootIndex()
        else:
            if self.file_model.isDir(index):
                parent_index = index
                parent_dir = self.file_model.filePath(index)
            else:
                parent_index = index.parent()
                parent_dir = self.file_model.filePath(parent_index)

        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        # collision-safe name
        folder_path = os.path.join(parent_dir, name)
        if os.path.exists(folder_path):
            folder_path = self._unique_dest_path(parent_dir, name)

        try:
            os.makedirs(folder_path, exist_ok=False)
            self.refresh_file_view()
            # try to select the new folder
            new_index = self.file_model.index(folder_path)
            if new_index.isValid():
                self.file_tree.setCurrentIndex(new_index)
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Failed to create folder — {e}")

    # Reveal in OS file explorer
    def _fs_reveal(self, index: QModelIndex):
        if not index or not index.isValid():
            return
        path = self.file_model.filePath(index)
        if not path:
            return

        try:
            if platform.system() == "Windows":
                # Explorer: select item if possible
                if os.path.isdir(path):
                    QProcess.startDetached("explorer", [path])
                else:
                    QProcess.startDetached("explorer", ["/select,", os.path.normpath(path)])
            elif platform.system() == "Darwin":
                # Finder: reveal
                QProcess.startDetached("/usr/bin/open", ["-R", path])
            else:
                # Fallback: open containing folder
                QProcess.startDetached("xdg-open", [os.path.dirname(path)])
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Reveal failed — {e}")
    # ---- End Context Menu + FS Helper Functions ----






    def load_selected_object(self, item):
        # Clear the view
        self.clear_view()
        
        # Load the selected object
        object_name = item.text()
        
        # Check if this is a file path
        if object_name in self.loaded_meshes:
            # If we've already loaded this mesh, use the cached data
            mesh_data = self.loaded_meshes[object_name]
            self.display_mesh_data(mesh_data, object_name)
            self.chat_history.append(f"<b>System:</b> Loaded {object_name}")
            return
        
        # Add message to chat history
        self.chat_history.append(f"<b>System:</b> Loaded {object_name}")
    
    def clear_view(self):
        # Clear the view
        self.view_widget.clear()
        
        # Add grid and axes
        grid = gl.GLGridItem()
        grid.setSize(x=20, y=20, z=0)
        grid.setSpacing(x=1, y=1, z=1)
        self.view_widget.addItem(grid)
        
        axes = gl.GLAxisItem()
        axes.setSize(x=5, y=5, z=5)
        self.view_widget.addItem(axes)
    

    
    def load_obj_file(self, file_path):
        """
        Load an OBJ file and display it in the 3D view with lighting.
        
        Args:
            file_path (str): Path to the OBJ file
        """
        self.chat_history.append(f"<b>System:</b> Loading OBJ file: {os.path.basename(file_path)}")
        
        try:
            # Load the mesh using trimesh
            mesh = trimesh.load(file_path, process=True)

            # Get vertices and faces
            vertices = mesh.vertices
            faces = mesh.faces

            # Normalize the model to fit in view
            center = np.mean(vertices, axis=0)
            vertices -= center
            max_distance = np.max(np.linalg.norm(vertices, axis=1))
            if max_distance > 0:
                scale_factor = 4.0 / max_distance
                vertices *= scale_factor

            # Compute vertex normals for better lighting
            mesh.vertices = vertices  # Update mesh with normalized vertices
            vertex_normals = mesh.vertex_normals

            # Apply lighting calculation
            colors = self.compute_lighting(vertices, faces, vertex_normals, mesh)

            # Create the GLMeshItem
            mesh_item = gl.GLMeshItem(
                vertexes=vertices, 
                faces=faces, 
                vertexColors=colors,  # Use vertex colors instead of face colors
                smooth=True,
                glOptions='opaque'
            )
            
            # Store mesh data for later reference
            file_name = os.path.basename(file_path)
            self.loaded_meshes[file_name] = {
                'vertices': vertices,
                'faces': faces,
                'mesh_item': mesh_item
            }
            
            # Clear the view and add the new mesh
            self.clear_view()
            self.view_widget.addItem(mesh_item)
            
            # Update window title
            self.setWindowTitle(f"3D Image Generator - {file_name}")
            
            self.chat_history.append(f"<b>System:</b> Successfully loaded {file_name}")
            return True
            
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Failed to load OBJ file. {str(e)}")
            return False
    
    def load_stl_file(self, file_path):
        """
        Load an STL file and display it in the 3D view with lighting.
        
        Args:
            file_path (str): Path to the STL file
        """
        self.chat_history.append(f"<b>System:</b> Loading STL file: {os.path.basename(file_path)}")
        
        try:
            # Load the mesh using trimesh
            mesh = trimesh.load(file_path)
            
            # Get vertices and faces
            vertices = mesh.vertices
            faces = mesh.faces
            
            # Normalize the model to fit in view
            center = np.mean(vertices, axis=0)
            vertices -= center  # Center the model at origin
            max_distance = np.max(np.linalg.norm(vertices, axis=1))
            if max_distance > 0:
                scale_factor = 4.0 / max_distance  # Scale to fit in view
                vertices *= scale_factor
            
            # Compute vertex normals for better lighting
            mesh.vertices = vertices
            vertex_normals = mesh.vertex_normals
            
            # Apply lighting calculation
            colors = self.compute_lighting(vertices, faces, vertex_normals, mesh)
            
            # Create a mesh item
            mesh_item = gl.GLMeshItem(
                vertexes=vertices, 
                faces=faces, 
                vertexColors=colors,  # Use vertex colors
                smooth=True,
                glOptions='opaque'
            )
            
            # Store mesh data for later reference
            file_name = os.path.basename(file_path)
            self.loaded_meshes[file_name] = {
                'vertices': vertices,
                'faces': faces,
                'mesh_item': mesh_item
            }
            
            # Clear the view and add the new mesh
            self.clear_view()
            self.view_widget.addItem(mesh_item)
            
            # Update window title
            self.setWindowTitle(f"3D Image Generator - {file_name}")
            
            self.chat_history.append(f"<b>System:</b> Successfully loaded {file_name}")
            return True
            
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Failed to load STL file. {str(e)}")
            return False
    def compute_lighting(self, vertices, faces, vertex_normals, mesh):
        """
        Compute lighting for the mesh using vertex normals.
        
        Args:
            vertices: Vertex positions
            faces: Face indices
            vertex_normals: Normal vectors for each vertex
            mesh: Trimesh object (for color information)
        
        Returns:
            colors: RGBA colors for each vertex with lighting applied
        """
        # Light direction (from top-front-right)
        light_direction = np.array([1.0, 1.0, 1.5])
        light_direction = light_direction / np.linalg.norm(light_direction)
        
        # Compute lighting intensity for each vertex
        # Dot product of normal and light direction
        lighting = np.dot(vertex_normals, light_direction)
        lighting = np.clip(lighting, 0, 1)  # Clamp to [0, 1]
        
        # Add ambient light
        ambient = 0.3
        lighting = ambient + (1.0 - ambient) * lighting
        
        # Get base colors from mesh if available
        if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
            base_colors = mesh.visual.vertex_colors[:, :3] / 255.0
        else:
            # Default gray color
            base_colors = np.full((len(vertices), 3), 0.7)
        
        # Apply lighting to colors
        colors = np.zeros((len(vertices), 4))
        colors[:, :3] = base_colors * lighting[:, np.newaxis]
        colors[:, 3] = 1.0  # Alpha channel
        
        return colors
        
    def display_mesh_data(self, mesh_data, name):
        """
        Display mesh data that's already been loaded.
        """
        if 'mesh_item' in mesh_data:
            self.view_widget.addItem(mesh_data['mesh_item'])
        else:
            vertices = mesh_data['vertices']
            faces = mesh_data['faces']
            colors = np.array([[0.7, 0.7, 0.7, 1.0] for _ in range(faces.shape[0])])
            mesh_item = gl.GLMeshItem(vertexes=vertices, faces=faces, faceColors=colors, smooth=True)
            self.view_widget.addItem(mesh_item)
            mesh_data['mesh_item'] = mesh_item
    
    def on_file_clicked(self, index):
        # Get the file path from the index
        file_path = self.file_model.filePath(index)
        
        # Check if it's a directory or file
        if os.path.isdir(file_path):
            # If it's a directory, just expand/collapse in the tree view
            self.chat_history.append(f"<b>System:</b> Opened folder: {os.path.basename(file_path)}")
            return
        
        # Check file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.obj':
            self.load_obj_file(file_path)
        elif ext.lower() == '.stl':
            self.load_stl_file(file_path)
        else:
            self.chat_history.append(f"<b>System:</b> Unsupported file format: {os.path.basename(file_path)}")
    
  
    def open_folder(self):
        # Open a dialog to select a folder
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder", self.current_directory)
        
        if folder_path:
            # Update the file tree view to show the selected folder
            self.current_directory = folder_path
            self.file_tree.setRootIndex(self.file_model.index(folder_path))
            self.chat_history.append(f"<b>System:</b> Opened folder: {os.path.basename(folder_path)}")
            
            # Save the last opened folder
            self.save_last_folder(folder_path)
        
    def save_last_folder(self, folder_path):
        try:
            with open("last_folder.txt", "w") as f:
                f.write(folder_path)
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Could not save last folder. {str(e)}")

    def load_last_folder(self):
        try:
            if os.path.exists("last_folder.txt"):
                with open("last_folder.txt", "r") as f:
                    folder_path = f.read().strip()
                    if os.path.isdir(folder_path):
                        return folder_path
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Could not load last folder. {str(e)}")
        
        return QDir.homePath()  # fallback if failed


    
    def create_new_folder(self):
        # Create a new folder in the current directory
        folder_name, ok = QFileDialog.getSaveFileName(self, "New Folder", self.current_directory, "")
        
        if ok and folder_name:
            try:
                os.makedirs(folder_name, exist_ok=True)
                self.chat_history.append(f"<b>System:</b> Created new folder: {os.path.basename(folder_name)}")
                self.refresh_file_view()
            except Exception as e:
                self.chat_history.append(f"<b>Error:</b> Failed to create folder. {str(e)}")
    
    def import_object(self):
        # Open file dialog for importing
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self, "Import 3D Object", self.current_directory,
            "3D Files (*.obj *.stl);;OBJ Files (*.obj);;STL Files (*.stl);;All Files (*)"
        )
        
        if file_path:
            # Load the selected file
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.obj':
                self.load_obj_file(file_path)
                folder_path = os.path.dirname(file_path)
                self.current_directory = folder_path
                self.file_tree.setRootIndex(self.file_model.index(folder_path))
            elif ext.lower() == '.stl':
                self.load_stl_file(file_path)
                folder_path = os.path.dirname(file_path)
                self.current_directory = folder_path
                self.file_tree.setRootIndex(self.file_model.index(folder_path))
            else:
                self.chat_history.append(f"<b>System:</b> Unsupported file format: {os.path.basename(file_path)}")
    
    def select_image_for_generation(self):
        """
        Open a file dialog to select an image for 3D model generation.
        """
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self, "Select Image for 3D Generation", self.current_directory,
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.chat_history.append(f"<b>System:</b> Selected image: {os.path.basename(file_path)}")
            self.chat_history.append("<b>System:</b> Click 'Generate' to create a 3D model from this image.")
            
            # Optionally update the text input to show image is selected
            self.chat_input.setPlaceholderText(f"Using image: {os.path.basename(file_path)}")

    
        
    def generate_3d_object(self):
        # Get user input
        user_input = self.chat_input.toPlainText().strip()
        # if both are empty
        # this allows the image name to be taken if the user does not add a prompt with the image
        if ((not user_input) and (not self.selected_image_path)):
            return

        # Determine what we're using for generation
        if self.selected_image_path:
            generation_info = f"image: {os.path.basename(self.selected_image_path)}"
            if user_input:
                generation_info += f" with prompt: {user_input}"
            
        else:
            generation_info = f"description: {user_input}"

        # Add user message to chat history
        self.chat_history.append(f"<b>You:</b> {generation_info}")
        self.chat_history.append("<b>AI:</b> Generating 3D object...")

        try:
            from datetime import datetime
            import shutil
            import random
            import re  # for cleaning filenames

            # Initialize the Gradio client
            client = Client("http://127.0.0.1:8080/")

            # Prepare image parameter
            image_param = handle_file(self.selected_image_path) if self.selected_image_path else None

            # Generate model using your AI backend
            result = client.predict(
                caption=user_input,
                image=image_param,
                mv_image_front=None,
                mv_image_back=None,
                mv_image_left=None,
                mv_image_right=None,
                steps=self.num_inference_steps,
                guidance_scale=self.guidance_scale,
                seed=1234,
                octree_resolution=self.octree_resolution,
                check_box_rembg=True,
                num_chunks=self.face_count,
                randomize_seed=True,
                api_name="/shape_generation"
            )

            # Unpack result (.glb file path is in result[0]["value"])
            mesh_file = result[0]["value"]

            # Define destination directory inside current working directory
            base_dir = os.getcwd()
            destination_dir = self.current_directory;
            os.makedirs(destination_dir, exist_ok=True)

            # Clean prompt for safe filename (replace spaces/symbols with underscores)
            if self.selected_image_path:
                # Use image filename as base if no text prompt
                if user_input:
                    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', user_input.strip())
                else:
                    image_basename = os.path.splitext(os.path.basename(self.selected_image_path))[0]
                    safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', image_basename)
            else:
                safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', user_input.strip())
            
            if not safe_name:
                safe_name = "generated_object"

            # Timestamp for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Create final base name
            base_name = f"{safe_name}_{timestamp}"

            # Copy .glb file to permanent folder
            glb_dest_path = os.path.join(destination_dir, f"{base_name}.glb")
            shutil.copy(mesh_file, glb_dest_path)
            self.chat_history.append(f"<b>System:</b> Saved generated .glb to {glb_dest_path}")

            # --- Export .obj using Gradio API ---
            export_result = client.predict(
                file_out=FileData(path=mesh_file),
                file_out2=FileData(path=mesh_file),
                file_type="obj",
                reduce_face=False,
                export_texture=False,
                target_face_num=10000,
                api_name="/on_export_click"
            )

            # Extract the .obj file path from result
            obj_temp_path = None
            if isinstance(export_result, (list, tuple)) and len(export_result) > 1:
                second_item = export_result[1]
                if isinstance(second_item, dict):
                    obj_temp_path = second_item.get("value")
                elif isinstance(second_item, str):
                    obj_temp_path = second_item
            elif isinstance(export_result, dict) and "value" in export_result:
                obj_temp_path = export_result["value"]

            if not obj_temp_path or not os.path.exists(obj_temp_path):
                raise FileNotFoundError(f"Exported OBJ path not found or invalid: {export_result}")

            # Move .obj to same Objects directory
            obj_dest_path = os.path.join(destination_dir, f"{base_name}.obj")
            shutil.copy(obj_temp_path, obj_dest_path)
            self.chat_history.append(f"<b>System:</b> Saved exported .obj to {obj_dest_path}")

            # Clear input box and reset image selection
            self.chat_input.clear()
            self.chat_input.setPlaceholderText("Describe the 3D image you want to generate...")
            self.selected_image_path = None

            # Add generated file to list and load it automatically
            display_name = f"{os.path.basename(obj_dest_path)}"
            item = QListWidgetItem(display_name)
            item.setData(256, obj_dest_path)  # Store path in user role
            self.objects_list.addItem(item)
            self.objects_list.setCurrentItem(item)
            self.load_selected_object(item)

            self.chat_history.append(f"<b>AI:</b> Finished creating 3D model based on your description!")

        except Exception as e:
            import traceback
            # self.chat_history.append(f"<b>Error:</b> 3D object generation failed — {e}")
            print(traceback.format_exc())

    
    def export_object(self):
        # Get the selected item from either the file tree or the objects list
        if self.tabs.currentIndex() == 0:  # File Explorer tab
            indexes = self.file_tree.selectedIndexes()
            if not indexes:
                self.chat_history.append("<b>System:</b> No file selected to export.")
                return
                
            file_path = self.file_model.filePath(indexes[0])
            if os.path.isdir(file_path):
                self.chat_history.append("<b>System:</b> Selected item is a directory, not a file.")
                return
                
            object_name = os.path.basename(file_path)


        # Open file dialog for exporting
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export 3D Object", os.path.join(self.current_directory, f"{object_name}.obj"),
            "OBJ Files (*.obj);;STL Files (*.stl);;All Files (*)"
        )

        if not file_path:
            return  # User canceled the export dialog

        # Determine format based on file extension
        file_format = "obj" if file_path.lower().endswith(".obj") else "stl"

        # Retrieve mesh data
        mesh_data = self.get_mesh_data(object_name)
        if not mesh_data:
            self.chat_history.append(f"<b>System:</b> Could not retrieve mesh data for {object_name}.")
            return

        vertices, faces = mesh_data

        # Write to file
        try:
            if file_format == "obj":
                self.save_as_obj(file_path, vertices, faces)
            else:
                self.save_as_stl(file_path, vertices, faces)

            self.chat_history.append(f"<b>System:</b> Successfully exported {object_name} to {file_path}.")
            self.refresh_file_view()
        except Exception as e:
            self.chat_history.append(f"<b>Error:</b> Failed to export {object_name}. {str(e)}")

    def get_mesh_data(self, object_name):
        """
        Returns the vertices and faces of the selected object.
        """
        if "Cube" in object_name:
            vertices = np.array([
                [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
            ])
            faces = np.array([
                [0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                [1, 2, 6], [1, 6, 5], [0, 3, 7], [0, 7, 4]
            ])
        elif "Sphere" in object_name:
            sphere = trimesh.creation.icosphere(radius=1, subdivisions=2)
            vertices, faces = sphere.vertices, sphere.faces
        elif "Cylinder" in object_name:
            cylinder = trimesh.creation.cylinder(radius=1, height=2)
            vertices, faces = cylinder.vertices, cylinder.faces
        elif "Pyramid" in object_name:
            vertices = np.array([
                [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0.5, 0.5, 1]
            ])
            faces = np.array([
                [0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4],
                [0, 1, 2], [0, 2, 3]
            ])
        else:
            # Default to cube if object type can't be determined
            vertices = np.array([
                [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
            ])
            faces = np.array([
                [0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7],
                [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                [1, 2, 6], [1, 6, 5], [0, 3, 7], [0, 7, 4]
            ])

        return vertices, faces

    def save_as_obj(self, file_path, vertices, faces):
        """
        Saves the mesh data as an OBJ file.
        """
        with open(file_path, "w") as file:
            for v in vertices:
                file.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for f in faces:
                file.write(f"f {f[0] + 1} {f[1] + 1} {f[2] + 1}\n")  # OBJ format is 1-based indexing

    def save_as_stl(self, file_path, vertices, faces):
        """
        Saves the mesh data as an STL file.
        """
        with open(file_path, "w") as file:
            file.write("solid object\n")
            for f in faces:
                v0, v1, v2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
                normal = np.cross(v1 - v0, v2 - v0)
                normal = normal / np.linalg.norm(normal) if np.linalg.norm(normal) != 0 else normal
                file.write(f"  facet normal {normal[0]} {normal[1]} {normal[2]}\n")
                file.write("    outer loop\n")
                for v in (v0, v1, v2):
                    file.write(f"      vertex {v[0]} {v[1]} {v[2]}\n")
                file.write("    endloop\n  endfacet\n")
            file.write("endsolid object\n")
    
    def refresh_file_view(self):
        """
        Refresh the file system view.
        """
        current_path = self.file_model.filePath(self.file_tree.rootIndex())
        self.file_model.setRootPath(current_path)
        self.file_tree.setRootIndex(self.file_model.index(current_path))
        self.chat_history.append("<b>System:</b> File view refreshed.")
    
    def toggle_hidden_files(self, state):
        """
        Toggle showing/hiding hidden files.
        """
        if state:
            self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot | QDir.Hidden)
            self.chat_history.append("<b>System:</b> Showing hidden files.")
        else:
            self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
            self.chat_history.append("<b>System:</b> Hiding hidden files.")
    
    def show_about(self):
        """
        Show about dialog.
        """
        self.chat_history.append(
            "<b>System:</b> 3D Image Generator v1.0<br>"
            "This tool was developed as part of our senior design course, CSE 448/449. It was created by:  "
            "Lindsey Koenig, Spencer McCrae, Ethan Varner, and Logan Lewton.<br><br>"
            "<b>About:</b> The 3D Image Generator is a tool designed to create, view, and export 3D models generated by "
            "an AI model. It integrates text prompts or images to an AI model with a 3D modeling pipeline, "
            "allowing generated models to be previewed and prepared for 3D printing.<br><br>"
            "<b>Instructions:</b><br>"
            "1. Enter a text prompt or upload an object.<br>"
            "2. Use the display window to rotate, zoom, and inspect the model.<br>"
            "3. Export the model to supported formats for use in CAD software or 3D printing.<br>"
            "4. Manage previously generated models through the project’s file manager.<br>"
            "5. You can change the settings of the model generation under the advanced settings tab.<br><br>" 
            "This program demonstrates our team’s combined efforts in front-end UI, back-end processing, "
            "API integration, and 3D printing workflows."
        )

class CustomSettingsDialog(QDialog):
    def __init__(self, parent, steps=80, guidance=7.5, faces=100000, octree=128):
        super().__init__(parent)
        self.setWindowTitle("Custom Settings")

        form = QFormLayout(self)

        # Steps
        self.steps = QSpinBox(self)
        self.steps.setRange(1, 500)
        self.steps.setValue(int(steps))
        form.addRow("Number of inference steps:", self.steps)

        # Guidance
        self.guidance = QDoubleSpinBox(self)
        self.guidance.setDecimals(2)
        self.guidance.setRange(0.0, 50.0)
        self.guidance.setSingleStep(0.1)
        self.guidance.setValue(float(guidance))
        form.addRow("Guidance scale:", self.guidance)

        # Faces
        self.faces = QSpinBox(self)
        self.faces.setRange(1000, 1_000_000)
        self.faces.setValue(int(faces))
        form.addRow("Face count:", self.faces)

        # Octree
        self.octree = QSpinBox(self)
        self.octree.setRange(8, 1024)
        self.octree.setValue(int(octree))
        form.addRow("Octree resolution:", self.octree)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return (
            int(self.steps.value()),
            float(self.guidance.value()),
            int(self.faces.value()),
            int(self.octree.value()),
        )



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThreeDImageGenerator()
    sys.exit(app.exec_())

