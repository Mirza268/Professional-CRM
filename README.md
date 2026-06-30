# Custom Enterprise CRM System (9-Module Suite)

A robust, lightweight, and professional full-stack Customer Relationship Management (CRM) system built with **Python (Flask)** and **SQLite3**. This application features a comprehensive multi-layered infrastructure distributed across 50 internal logical pages/sections, covering everything from core financial pipelines to advanced system audit logging.

## 🚀 Key Features & Enterprise Modules

The application is structured into **9 dedicated core modules**, each handling a critical business workflow:

1. **🔒 Master Authentication & Role Management**
   - Secure User Registration, Session Login, and Logout functionality.
   - Granular RBAC (Role-Based Access Control) with roles: `Admin`, `Manager`, and `Employee`.
2. **📈 Centralized Dashboard**
   - Live system-wide metrics overview.
   - Dynamic tracking of total revenue, open leads, task completions, and recent activities.
3. **🎯 Sales & Lead Management Pipeline**
   - Complete CRUD operations for potential customer leads.
   - Pipeline stages: `New`, `In Progress`, `Won`, and `Lost`.
4. **💼 Client & Contact Directory**
   - Consolidated master database for verified clients.
   - Secure storage of corporate emails, primary phone networks, and account history.
5. **🛠️ Operational Task Orchestrator**
   - Task allocation engine with assignments mapped to specific users.
   - Priority status controls (`Pending`, `In Progress`, `Completed`) with automatic dependency checking.
6. **📊 Financial Billings & Invoice Engine**
   - Automatic generation of corporate invoices.
   - Keeps track of payment records, total billable amounts, and statuses (`Paid`, `Unpaid`, `Overdue`).
7. **📢 Multi-Channel Marketing Hub**
   - Campaign scheduling and audience outreach tracking tool.
   - Tracks conversions across multiple channels (`Email`, `Social Media`, `Cold Call`).
8. **👥 Master User Matrix Panel (Admin Restricted)**
   - Secure directory visible exclusively to system administrators.
   - Allows oversight of all registered user network identities and permission levels.
9. **🛡️ Global System Audit Logger**
   - High-security system logs tracking critical database mutations and platform activity.
   - Timestamped records of major operations for regulatory and security compliance.

---

## 🛠️ Tech Stack & Architecture

- **Backend Framework:** Python (Flask)
- **Database Engine:** SQLite3 (Embedded SQL relational database)
- **Frontend Layer:** Dynamic HTML Context Injection (`render_template_string` rendering 50 interconnected logical UI views)
- **Style Language:** Standard inline CSS layout structuring

---

## 💻 Installation & Local Setup

Follow these simple steps to spin up the enterprise CRM on your local environment:

### Prerequisites
Make sure you have **Python 3.x** and `pip` installed on your machine. You can verify by running:
```bash
python --version
1. Clone the Repository
Bash
git clone [https://github.com/YOUR_USERNAME/crm-system.git](https://github.com/YOUR_USERNAME/crm-system.git)
cd crm-system
2. Install Required Dependencies
The project relies completely on Flask for lightweight container routing. Run:

Bash
pip install flask
3. Initialize & Run the Application
Execute the master Python file. The system will automatically build the SQLite schema file (database.db) on its initial boot:

Bash
python app.py
4. Open in Browser
Once the terminal outputs Running on http://127.0.0.1:5000, open your web browser and navigate to the registration endpoint to create your first administrative root account:

Plaintext
[http://127.0.0.1:5000/register](http://127.0.0.1:5000/register)
📂 Project Structure
Plaintext
crm_system/
├── app.py              # Main application script containing routing and database initialization
├── database.db         # SQLite database file (Automatically generated on first run)
└── README.md           # Documentation and project manual
🛡️ Security & Role Permissions Matrix
Admin: Unrestricted global root access (Access to Master User Matrix, Audit Logs, and full financial operations).

Manager: Full access to Sales, Clients, Marketing, and Task assignments (Restricted from core system security logs/user admin panels).

Employee: Execution-focused access limited to managing active Tasks, Leads, and updating specific pipeline records.
