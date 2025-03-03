from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QGroupBox, QSpinBox,
                             QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import Qt, QSettings


class PreferencesDialog(QDialog):
    """Dialog for setting application preferences, particularly related to Kanban board and concurrency."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("MedicalPatientManager", "KanbanBoard")
        self.initUI()
        self.loadSettings()
        
    def initUI(self):
        """Initialize the UI elements for the preferences dialog."""
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Concurrency settings group
        concurrency_group = QGroupBox("Concurrency Settings")
        concurrency_layout = QFormLayout()
        
        # Conflict resolution mode
        self.conflict_mode_combo = QComboBox()
        self.conflict_mode_combo.addItem("Automatic (Last Writer Wins)", "last_wins")
        self.conflict_mode_combo.addItem("Manual Resolution", "manual")
        concurrency_layout.addRow("Conflict Resolution:", self.conflict_mode_combo)
        
        # Refresh interval
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(1)
        self.refresh_interval_spin.setMaximum(60)
        self.refresh_interval_spin.setSuffix(" seconds")
        concurrency_layout.addRow("Refresh Interval:", self.refresh_interval_spin)
        
        concurrency_group.setLayout(concurrency_layout)
        layout.addWidget(concurrency_group)
        
        # Description of settings
        desc_label = QLabel(
            "Automatic resolution will silently apply the most recent changes.\n"
            "Manual resolution will prompt you to choose what to do when conflicts occur.\n"
            "Refresh interval determines how often the system checks for changes made by other users."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.saveSettings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def loadSettings(self):
        """Load current settings from QSettings."""
        # Load conflict resolution mode
        conflict_mode = self.settings.value("conflict_resolution_mode", "last_wins")
        index = self.conflict_mode_combo.findData(conflict_mode)
        if index >= 0:
            self.conflict_mode_combo.setCurrentIndex(index)
            
        # Load refresh interval
        refresh_interval = int(self.settings.value("refresh_interval", 5000))
        self.refresh_interval_spin.setValue(refresh_interval // 1000)  # Convert ms to seconds
        
    def saveSettings(self):
        """Save settings to QSettings and close dialog."""
        # Save conflict resolution mode
        conflict_mode = self.conflict_mode_combo.currentData()
        self.settings.setValue("conflict_resolution_mode", conflict_mode)
        
        # Save refresh interval (convert seconds to milliseconds)
        refresh_interval = self.refresh_interval_spin.value() * 1000
        self.settings.setValue("refresh_interval", refresh_interval)
        
        self.accept()
