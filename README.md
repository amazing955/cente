# Automated Tape Inventory Management System

## Overview

The **Automated Tape Inventory Management System (ATIMS)** is an enterprise-grade web application developed using **Django** and **PostgreSQL** to automate the management, tracking, transportation, auditing, and lifecycle of backup tapes within an organization.

The system is designed for environments such as banks, government institutions, and large enterprises where secure backup media management, chain of custody, and compliance are essential.

---

# Key Features

* Secure user authentication and role-based access control
* Dynamic dashboard based on assigned features and permissions
* Tape inventory management
* Barcode and VolSER tracking
* Shipment creation and management
* Shipment approval workflow
* Return shipment workflow
* Courier assignment and reassignment
* Exception reporting and investigation
* Chain of custody tracking
* Audit trail
* System logging
* Notification center
* Email notifications
* Excel import and export
* Dynamic branch management
* API integration
* JWT-secured REST APIs
* Dashboard analytics
* Compliance reporting

---

# Technologies Used

## Backend

* Python
* Django
* Django REST Framework
* Django Channels (for real-time features)
* PostgreSQL

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* AJAX

## Authentication

* JWT (JSON Web Token)
* Django Authentication
* Role-Based Access Control (RBAC)

---

# System Roles

The system supports multiple user roles including:

* Super Administrator
* Backup Administrator
* Operations Manager
* Courier
* Compliance Auditor
* Internal Auditor
* Branch User
* IT Administrator

Each role is granted permissions through the role and feature management system.

---

# Major Modules

## Dashboard

Provides role-specific dashboards displaying:

* Statistics
* Notifications
* Pending approvals
* Recent activities
* Shipment summaries

---

## Inventory Management

Manage backup tapes including:

* Tape registration
* Barcode management
* VolSER management
* Manufacturer
* Tape type
* Current location
* Status tracking
* Retention dates

---

## Shipment Management

Supports the complete shipment lifecycle.

Workflow includes:

1. Shipment Request
2. Approval
3. Tape Assignment
4. Courier Assignment
5. Courier Acceptance
6. Dispatch
7. Delivery
8. Receipt Confirmation
9. Return Request
10. Return Approval
11. Shipment Completion

---

## Return Workflow

Operations Manager initiates a return.

Backup Administrator receives approval request.

Courier is assigned.

Courier accepts assignment.

Courier returns tape.

Backup Administrator receives shipment.

Shipment is marked as completed.

Every stage is logged.

---

## Exception Management

Supports reporting and investigation of exceptions.

Examples:

* Missing tape
* Barcode mismatch
* Wrong location
* Unauthorized movement
* Inventory discrepancies

---

## Investigation Dashboard

Displays:

* Shipment history
* Tape history
* User interactions
* Notifications
* Audit logs
* Timeline
* Chain of custody
* Compliance analysis

---

## Notifications

Supports:

* In-system notifications
* Email notifications

Notifications are generated for:

* Shipment approval
* Courier assignment
* Return requests
* Shipment completion
* Exceptions
* Administrative actions

---

## Audit Trail

Every important action is recorded.

Audit data includes:

* User
* Role
* Timestamp
* Previous value
* New value
* IP Address
* Module
* Description

---

## API

REST APIs are secured using JWT authentication.

Features include:

* Login
* Refresh Token
* Shipment APIs
* Inventory APIs
* Exception APIs
* Investigation APIs
* Notification APIs

---

# Security

The application includes:

* JWT Authentication
* Role-Based Access Control
* Secure Password Hashing
* Audit Logging
* Permission-Based Access
* API Authentication
* Refresh Tokens
* HTTPS-ready configuration

---

# Database

Primary database:

PostgreSQL

The system also supports:

* Automatic branch uploads
* Excel imports
* Schema synchronization for approved templates

---

# Installation

Clone the repository.

Create a virtual environment.

Install dependencies.

Run migrations.

Create a superuser.

Start the development server.

---

# Requirements

* Python 3.11+
* PostgreSQL
* Django
* Django REST Framework
* Bootstrap 5

---

# Future Improvements

* Android mobile application
* Push notifications
* GPS tracking for couriers
* QR code support
* RFID integration
* AI-powered anomaly detection
* Advanced analytics
* Document management
* Electronic signatures
* Multi-tenant support

---

# License

This project is intended for educational and enterprise deployment purposes.

---

# Author

**Clinton Atulinde**

Applied Information Technology

Java Developer

Django Developer

NextSolutech

Innovation. Code. Future.
