# 🔒 Hardened Enterprise CRM System

A production-ready, security-hardened Customer Relationship Management (CRM) system built with **Python (Flask)** and **SQLite3**.

---

## 🚀 What's New (Hardened Version)

### Security Hardening
- **Password Hashing**: All passwords stored with `werkzeug.security` (bcrypt-style PBKDF2)
- **CSRF Protection**: Every POST form includes CSRF token validation
- **Authentication Required**: All routes properly protected with `@login_required`
- **Role-Based Access Control**: `@role_required('Admin', 'Manager')` enforces RBAC
- **Session Security**: Secure cookies, HttpOnly, SameSite=Lax, 2-hour timeout
- **Input Validation**: Email regex, phone validation, length limits, XSS prevention
- **SQL Injection Prevention**: 100% parameterized queries, no string concatenation
- **Stock Validation**: Prevents negative inventory
- **Self-Deletion Prevention**: Admins cannot delete their own account

### Bug Fixes
- **Fixed**: Empty `create_invoice.html` template
- **Fixed**: Duplicate DOCTYPE in `payments_log.html`
- **Fixed**: Missing `audit_logs.html` template
- **Fixed**: All delete links converted to POST forms with confirmation
- **Fixed**: Task archive now queries only completed tasks in SQL
- **Fixed**: Foreign key constraints enabled (`PRAGMA foreign_keys = ON`)
- **Fixed**: Amounts stored as INTEGER cents (no float precision issues)

### Database Improvements
- **Indexes**: Added on `leads(status)`, `deals(stage)`, `tasks(assigned_to)`, etc.
- **Timestamps**: `created_at`, `updated_at`, `last_login`, `paid_at` on all tables
- **Foreign Keys**: Proper `ON DELETE SET NULL` behavior
- **CHECK Constraints**: Enum validation at database level
- **Audit Trail**: `user_id` added to audit_logs for accountability

### UI/UX Improvements
- **Responsive Design**: Mobile-friendly layouts with CSS Grid/Flexbox
- **Flash Messages**: Styled success/error/warning/info notifications
- **Modern Styling**: Clean cards, hover effects, color-coded badges
- **Consistent Navigation**: All pages link back to dashboard
- **Chat Improvements**: Shows usernames instead of raw IDs, message bubbles
- **Dashboard Stats**: Live metrics for leads, deals, revenue, tasks, stock

---

## 📦 Installation

```bash
# 1. Clone / extract the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Set a secure secret key (production)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 4. Run the application
python app.py

# 5. Open in browser
# http://127.0.0.1:5000/register
```

---

## 🛡️ Security Checklist

| Feature | Status |
|---------|--------|
| Password Hashing (PBKDF2) | ✅ |
| CSRF Token Protection | ✅ |
| Session Security (HttpOnly, Secure, SameSite) | ✅ |
| Input Validation & Sanitization | ✅ |
| SQL Injection Prevention | ✅ |
| Role-Based Access Control | ✅ |
| Audit Logging | ✅ |
| Secure Error Pages | ✅ |
| Delete Confirmation (POST only) | ✅ |
| Negative Stock Prevention | ✅ |

---

## 👥 Role Permissions

| Route | Admin | Manager | Employee |
|-------|-------|---------|----------|
| Dashboard, Leads, Deals, Quotes | ✅ | ✅ | ✅ |
| Inventory, Tasks, Chat, Documents | ✅ | ✅ | ✅ |
| Invoices, Finance Summary | ✅ | ✅ | ✅ |
| Audit Logs | ✅ | ✅ | ❌ |
| User Management (/admin/users) | ✅ | ❌ | ❌ |
| System Backup, Cache Flush | ✅ | ❌ | ❌ |

---

## 🗄️ Database Schema

### users
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| username | TEXT | NOT NULL |
| email | TEXT | UNIQUE, NOT NULL |
| password_hash | TEXT | NOT NULL |
| role | TEXT | CHECK(Admin/Manager/Employee) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| last_login | TIMESTAMP | |

### leads
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | NOT NULL |
| email | TEXT | |
| phone | TEXT | |
| status | TEXT | CHECK(New/Contacted/Qualified/Lost) |
| created_by | INTEGER | FK → users |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### deals
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| title | TEXT | NOT NULL |
| amount | INTEGER | NOT NULL (cents) |
| stage | TEXT | CHECK(Prospect/Proposal/Negotiation/Closed Won/Closed Lost) |
| lead_id | INTEGER | FK → leads(ON DELETE SET NULL) |
| created_by | INTEGER | FK → users |

### products
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | NOT NULL |
| sku | TEXT | UNIQUE, NOT NULL |
| price | INTEGER | NOT NULL (cents) |
| stock | INTEGER | DEFAULT 0, CHECK(stock >= 0) |

### invoices
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| client_name | TEXT | NOT NULL |
| amount | INTEGER | NOT NULL (cents) |
| status | TEXT | CHECK(Paid/Unpaid/Overdue) |
| created_by | INTEGER | FK → users |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| paid_at | TIMESTAMP | |

### tasks
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| title | TEXT | NOT NULL |
| description | TEXT | |
| due_date | TEXT | |
| priority | TEXT | CHECK(Low/Medium/High) |
| status | TEXT | CHECK(Pending/In Progress/Completed) |
| assigned_to | INTEGER | FK → users |
| created_by | INTEGER | FK → users |

### messages
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| sender_id | INTEGER | FK → users |
| text | TEXT | NOT NULL |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### audit_logs
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| user_id | INTEGER | FK → users |
| action | TEXT | NOT NULL |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### documents
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| filename | TEXT | NOT NULL |
| uploaded_by | INTEGER | FK → users |
| uploaded_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

---

## 🔌 API Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| GET /api/users/count | Required | Total registered users |
| GET /api/leads/analytics | Required | Lead status breakdown |
| GET /api/deals/value | Required | Active pipeline value |
| GET /api/finance/active-ledger | Required | Invoice ledger (JSON) |
| GET /system/health | Public | Health check |

---

## 📝 File Structure

```
crm_system/
├── app.py                    # Main application (hardened)
├── requirements.txt          # Dependencies
├── database.db               # SQLite database (auto-created)
├── README.md                 # This file
└── templates/
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── leads.html
    ├── add_lead.html
    ├── edit_lead.html
    ├── view_lead.html
    ├── status_lead.html
    ├── pipeline.html
    ├── add_deal.html
    ├── move_deal.html
    ├── inventory.html
    ├── add_product.html
    ├── edit_product.html
    ├── stocks.html
    ├── quotes.html
    ├── create_quote.html
    ├── view_quote.html
    ├── invoice.html
    ├── create_invoice.html
    ├── view_invoice.html
    ├── payment_gate.html
    ├── billing_summary.html
    ├── payments_log.html
    ├── tasks.html
    ├── create_task.html
    ├── view_task.html
    ├── edit_task_status.html
    ├── tasks_archive.html
    ├── chat.html
    ├── documents.html
    ├── audit_logs.html
    ├── admin_users.html
    ├── error.html
    ├── system_message.html
    ├── announcement.html
    └── metric_display.html
```

---

## ⚠️ Production Deployment Notes

1. **Set a strong SECRET_KEY** environment variable
2. **Use HTTPS** (SESSION_COOKIE_SECURE=True requires HTTPS)
3. **Run with a WSGI server** (Gunicorn/uWSGI), not Flask dev server
4. **Use a reverse proxy** (Nginx) for SSL termination
5. **Backup database regularly** via /admin/system/backup-trigger
6. **Monitor audit logs** at /system/logs

---

## 🔄 Migration from Original

The database schema has changed. To migrate existing data:

1. Backup your original `database.db`
2. Delete the old `database.db` (schema incompatible)
3. Run `python app.py` to create new schema
4. Re-register users (passwords will be properly hashed)

---

*Hardened and modernized by AI Security Review — 2026*
