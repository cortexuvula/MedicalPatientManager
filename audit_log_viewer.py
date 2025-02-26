"""
Audit Log Viewer for Medical Patient Manager.

This module provides a dialog for viewing and filtering audit logs.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                           QLineEdit, QPushButton, QDateEdit, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QCheckBox, QGroupBox,
                           QFormLayout, QSpinBox, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QDate

import csv
import json
from datetime import datetime, timedelta

from models import AuditLog
from security import PermissionManager, sanitize_data_for_logs


class AuditLogViewer(QDialog):
    """Dialog for viewing and filtering audit logs."""
    
    def __init__(self, db, current_user, parent=None):
        """Initialize the audit log viewer.
        
        Args:
            db: Database instance
            current_user: Current user object
            parent: Parent widget
        """
        super().__init__(parent)
        self.db = db
        self.current_user = current_user
        
        # Check if user has permission to view audit logs
        if not PermissionManager.has_permission(current_user, 'audit.view'):
            QMessageBox.warning(self, "Access Denied", 
                             "You do not have permission to view audit logs.")
            self.reject()
            return
            
        self.setWindowTitle("Audit Log Viewer")
        self.resize(1000, 600)
        
        self.initUI()
        self.loadAuditLogs()
    
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout()
        
        # Filter section
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()
        
        # User filter
        self.user_filter = QComboBox()
        self.user_filter.addItem("All Users", None)
        users = self.db.get_all_users()
        for user in users:
            self.user_filter.addItem(f"{user.username} ({user.name})", user.id)
        filter_layout.addRow("User:", self.user_filter)
        
        # Action filter
        self.action_filter = QComboBox()
        self.action_filter.addItem("All Actions", None)
        actions = [
            AuditLog.ACTION_CREATE,
            AuditLog.ACTION_READ,
            AuditLog.ACTION_UPDATE,
            AuditLog.ACTION_DELETE,
            AuditLog.ACTION_LOGIN,
            AuditLog.ACTION_LOGOUT,
            AuditLog.ACTION_SHARE,
            AuditLog.ACTION_REVOKE,
            AuditLog.ACTION_EXPORT,
            AuditLog.ACTION_IMPORT,
            AuditLog.ACTION_SEARCH,
            AuditLog.ACTION_REPORT,
            AuditLog.ACTION_PERMISSION_CHANGE,
            AuditLog.ACTION_PASSWORD_CHANGE,
            AuditLog.ACTION_PASSWORD_RESET,
            AuditLog.ACTION_ACCOUNT_CREATE,
            AuditLog.ACTION_ACCOUNT_DISABLE,
            AuditLog.ACTION_SYSTEM_CONFIG,
            AuditLog.ACTION_FAILED_LOGIN
        ]
        for action in actions:
            self.action_filter.addItem(action.replace('_', ' ').title(), action)
        filter_layout.addRow("Action:", self.action_filter)
        
        # Entity type filter
        self.entity_type_filter = QComboBox()
        self.entity_type_filter.addItem("All Entities", None)
        entity_types = [
            AuditLog.ENTITY_PATIENT,
            AuditLog.ENTITY_PROGRAM,
            AuditLog.ENTITY_TASK,
            AuditLog.ENTITY_USER,
            AuditLog.ENTITY_SYSTEM,
            AuditLog.ENTITY_REPORT,
            AuditLog.ENTITY_AUDIT
        ]
        for entity_type in entity_types:
            self.entity_type_filter.addItem(entity_type.title(), entity_type)
        filter_layout.addRow("Entity Type:", self.entity_type_filter)
        
        # Entity ID filter
        self.entity_id_filter = QLineEdit()
        filter_layout.addRow("Entity ID:", self.entity_id_filter)
        
        # Date range filters
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # Default to last 30 days
        self.start_date.setCalendarPopup(True)
        filter_layout.addRow("Start Date:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())  # Default to today
        self.end_date.setCalendarPopup(True)
        filter_layout.addRow("End Date:", self.end_date)
        
        # Quick date ranges
        date_ranges_layout = QHBoxLayout()
        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(self.set_today_range)
        self.week_btn = QPushButton("Last 7 Days")
        self.week_btn.clicked.connect(self.set_week_range)
        self.month_btn = QPushButton("Last 30 Days")
        self.month_btn.clicked.connect(self.set_month_range)
        
        date_ranges_layout.addWidget(self.today_btn)
        date_ranges_layout.addWidget(self.week_btn)
        date_ranges_layout.addWidget(self.month_btn)
        filter_layout.addRow("Quick Ranges:", date_ranges_layout)
        
        # Results limit
        self.limit_spin = QSpinBox()
        self.limit_spin.setMinimum(10)
        self.limit_spin.setMaximum(1000)
        self.limit_spin.setValue(100)
        self.limit_spin.setSingleStep(10)
        filter_layout.addRow("Max Results:", self.limit_spin)
        
        # Only critical events checkbox
        self.critical_only = QCheckBox("Show Only Critical Events")
        filter_layout.addRow("", self.critical_only)
        
        # Apply filters button
        self.apply_filter_btn = QPushButton("Apply Filters")
        self.apply_filter_btn.clicked.connect(self.loadAuditLogs)
        filter_layout.addRow("", self.apply_filter_btn)
        
        # Show all logs button
        self.show_all_btn = QPushButton("Show All Logs")
        self.show_all_btn.clicked.connect(self.showAllLogs)
        filter_layout.addRow("", self.show_all_btn)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # Results table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(8)
        self.log_table.setHorizontalHeaderLabels([
            "ID", "Timestamp", "User", "Action", "Entity Type", 
            "Entity ID", "IP Address", "Details"
        ])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)  # Make details column stretch
        
        main_layout.addWidget(self.log_table)
        
        # Export button
        export_layout = QHBoxLayout()
        self.export_csv_btn = QPushButton("Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_json_btn = QPushButton("Export to JSON")
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addStretch()
        export_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(export_layout)
        
        self.setLayout(main_layout)
    
    def loadAuditLogs(self):
        """Load audit logs with current filter settings."""
        # Get filter values
        user_id = self.user_filter.currentData()
        action = self.action_filter.currentData()
        entity_type = self.entity_type_filter.currentData()
        entity_id = self.entity_id_filter.text() or None
        
        # Convert entity_id to int if it's numeric
        if entity_id and entity_id.isdigit():
            entity_id = int(entity_id)
        
        # Get date range
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # Get limit
        limit = self.limit_spin.value()
        
        print(f"Retrieving audit logs with filters:")
        print(f"  user_id: {user_id}")
        print(f"  action: {action}")
        print(f"  entity_type: {entity_type}")
        print(f"  entity_id: {entity_id}")
        print(f"  start_date: {start_date}")
        print(f"  end_date: {end_date}")
        print(f"  limit: {limit}")
        
        # Query logs from database
        logs = self.db.get_audit_logs(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        print(f"Retrieved {len(logs)} audit logs")
        
        # Filter by severity if critical only is checked
        if self.critical_only.isChecked():
            logs = [log for log in logs if log.severity == AuditLog.SEVERITY_CRITICAL]
            print(f"After severity filtering: {len(logs)} logs")
        
        # Update the table
        self.log_table.setRowCount(0)  # Clear existing rows
        for row, log in enumerate(logs):
            self.log_table.insertRow(row)
            
            # Get username for user_id
            username = "Unknown"
            user = self.db.get_user_by_id(log.user_id)
            if user:
                username = user.username
            
            # Set cell values
            self.log_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            
            # Format timestamp nicely
            timestamp = log.get_formatted_timestamp()
            self.log_table.setItem(row, 1, QTableWidgetItem(timestamp))
            
            self.log_table.setItem(row, 2, QTableWidgetItem(username))
            self.log_table.setItem(row, 3, QTableWidgetItem(log.action))
            self.log_table.setItem(row, 4, QTableWidgetItem(log.entity_type))
            self.log_table.setItem(row, 5, QTableWidgetItem(str(log.entity_id) if log.entity_id else ""))
            self.log_table.setItem(row, 6, QTableWidgetItem(log.ip_address))
            
            # Ensure details are sanitized before display
            details = log.details
            if details:
                try:
                    # Try to parse as JSON and sanitize
                    details_dict = json.loads(details)
                    sanitized = sanitize_data_for_logs(details_dict)
                    details = json.dumps(sanitized, indent=2)
                except json.JSONDecodeError:
                    # Not JSON, just use as is
                    pass
                    
            self.log_table.setItem(row, 7, QTableWidgetItem(details or ""))
            
            # Color code critical events
            if hasattr(log, 'severity') and log.severity == AuditLog.SEVERITY_CRITICAL:
                for col in range(self.log_table.columnCount()):
                    item = self.log_table.item(row, col)
                    if item:
                        item.setBackground(Qt.red)
                        item.setForeground(Qt.white)
    
    def showAllLogs(self):
        """Show all audit logs."""
        # Clear filter values
        self.user_filter.setCurrentIndex(0)
        self.action_filter.setCurrentIndex(0)
        self.entity_type_filter.setCurrentIndex(0)
        self.entity_id_filter.clear()
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # Default to last 30 days
        self.end_date.setDate(QDate.currentDate())  # Default to today
        self.limit_spin.setValue(100)
        self.critical_only.setChecked(False)
        
        # Load audit logs
        self.loadAuditLogs()
    
    def set_today_range(self):
        """Set the date range to today only."""
        today = QDate.currentDate()
        self.start_date.setDate(today)
        self.end_date.setDate(today)
    
    def set_week_range(self):
        """Set the date range to the last 7 days."""
        today = QDate.currentDate()
        last_week = today.addDays(-7)
        self.start_date.setDate(last_week)
        self.end_date.setDate(today)
    
    def set_month_range(self):
        """Set the date range to the last 30 days."""
        today = QDate.currentDate()
        last_month = today.addDays(-30)
        self.start_date.setDate(last_month)
        self.end_date.setDate(today)
    
    def export_to_csv(self):
        """Export the current audit log results to a CSV file."""
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Audit Logs", "", "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                
                # Write header
                header = []
                for col in range(self.log_table.columnCount()):
                    header.append(self.log_table.horizontalHeaderItem(col).text())
                writer.writerow(header)
                
                # Write data
                for row in range(self.log_table.rowCount()):
                    row_data = []
                    for col in range(self.log_table.columnCount()):
                        item = self.log_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
                    
            QMessageBox.information(self, "Export Successful", 
                                 f"Audit logs exported to {file_path}")
                                 
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", 
                               f"Failed to export audit logs: {str(e)}")
    
    def export_to_json(self):
        """Export the current audit log results to a JSON file."""
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Audit Logs", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            logs = []
            header = []
            for col in range(self.log_table.columnCount()):
                header.append(self.log_table.horizontalHeaderItem(col).text())
                
            for row in range(self.log_table.rowCount()):
                log_entry = {}
                for col in range(self.log_table.columnCount()):
                    item = self.log_table.item(row, col)
                    log_entry[header[col]] = item.text() if item else ""
                logs.append(log_entry)
                
            with open(file_path, 'w') as json_file:
                json.dump(logs, json_file, indent=2)
                    
            QMessageBox.information(self, "Export Successful", 
                                 f"Audit logs exported to {file_path}")
                                 
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", 
                               f"Failed to export audit logs: {str(e)}")
