# ComptaGo — AI Vision Migration Plan

> **Date:** March 2026  
> **Status:** Planning  
> **Author:** ComptaGo Team

---
test
## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [AI Provider Comparison](#3-ai-provider-comparison)
4. [Phase 1 — Multi-Provider AI Vision Backend](#4-phase-1--multi-provider-ai-vision-backend)
5. [Phase 2 — Bank Statement AI Vision](#5-phase-2--bank-statement-ai-vision)
6. [Phase 3 — Frontend PWA Conversion](#6-phase-3--frontend-pwa-conversion)
7. [Phase 4 — Mobile PWA Features](#7-phase-4--mobile-pwa-features)
8. [Phase 5 — Testing & QA](#8-phase-5--testing--qa)
9. [Phase 6 — Deployment & Rollout](#9-phase-6--deployment--rollout)
10. [File Reference Map](#10-file-reference-map)
11. [Risk Assessment](#11-risk-assessment)
12. [Timeline](#12-timeline)

---

## 1. Executive Summary

### Problem

The current OCR pipeline uses **pytesseract + OpenCV preprocessing → raw text → GPT-4/regex extraction**. This creates several issues:

- OCR errors propagate to AI (e.g., `até` instead of `Qté`, broken table layouts)
- ~2000 lines of fragile regex patterns in `invoice_parser.py`
- No table structure awareness (loses columns, headers, alignment)
- Image preprocessing is manual and error-prone
- Single AI provider (OpenAI GPT-4) — vendor lock-in
- No mobile support for on-the-go invoice capture

### Solution

1. **Replace OCR + text extraction with AI Vision models** that process images directly (Claude, GPT-4o)
2. **Multi-provider fallback** — no vendor lock-in
3. **Convert frontend to PWA** — mobile invoice capture via camera, offline support
4. **Extend to bank statements** — same vision approach

### Expected Improvements

| Metric                     | Current                  | After Migration                  |
| -------------------------- | ------------------------ | -------------------------------- |
| Invoice parsing accuracy   | ~70-80% (OCR-dependent)  | ~92-97% (vision models)          |
| Table/line-item extraction | Poor (regex-based)       | Excellent (layout-aware)         |
| Moroccan invoice support   | Partial (regex patterns) | Full (AI understands context)    |
| Processing time            | ~8-15s (OCR + GPT-4)     | ~3-8s (vision direct)            |
| Mobile support             | None                     | Full PWA + Camera capture        |
| Provider flexibility       | OpenAI only              | Claude + GPT-4o + regex fallback |
| Code maintenance           | ~2000 lines regex        | ~300 lines AI orchestration      |

---

## 2. Current Architecture Analysis

### 2.1 Invoice Processing Pipeline (Current)

```
Upload (PDF/JPG/PNG)
    │
    ▼
┌───────────────────────────────────────────────┐
│  InvoiceParser.extract_text_from_file()       │
│  ├─ PDF → pdf2image → convert_from_bytes()    │
│  ├─ Image → PIL.Image.open()                  │
│  ├─ Preprocessing → OpenCV (grayscale, blur)  │
│  └─ OCR → pytesseract.image_to_string()       │
│                                               │
│  File: src/apps/invoices/invoice_parser.py     │
│  Lines: ~2073 total                           │
└──────────────┬────────────────────────────────┘
               │ raw text
               ▼
    ┌─── GPT_USE_GPT_4 setting? ───┐
    │ YES                          │ NO
    ▼                              ▼
┌──────────────────┐    ┌──────────────────────┐
│ GPTInvoiceParser │    │ Regex extraction     │
│ gpt_invoice_     │    │ FIELD_PATTERNS dict  │
│ parser.py        │    │ ~500 lines of regex  │
│ (GPT-4 text API) │    │ per language (en/fr) │
└──────┬───────────┘    └──────────┬───────────┘
       │                           │
       └─────────┬─────────────────┘
                 ▼
         Structured JSON data
                 │
                 ▼
┌────────────────────────────────────────────┐
│ InvoiceViewSet (views.py)                  │
│ → Creates Invoice + InvoiceLineItem models │
│ → Matches/creates Supplier & Customer      │
│                                            │
│ File: src/apps/invoices/views.py           │
│ Lines: ~1410 total                         │
└────────────────────────────────────────────┘
```

### 2.2 Bank Statement Pipeline (Current)

```
Upload (PDF/CSV/Excel/Image)
    │
    ▼
┌────────────────────────────────────────────────┐
│ StatementParser.parse_statement()               │
│ ├─ PDF → pdfplumber/pytesseract               │
│ ├─ CSV → csv.reader                           │
│ ├─ Excel → openpyxl                           │
│ └─ Image → pytesseract                        │
│                                                │
│ File: src/apps/bank_statements/               │
│       statement_parser.py (~267 lines)        │
└──────────────┬─────────────────────────────────┘
               │ raw text
               ▼
┌────────────────────────────────────────────────┐
│ GPTStatementParser (gpt-3.5-turbo-16k)        │
│ → Extracts bank name, transactions, balances  │
│ → TransactionMapper normalizes categories     │
│                                                │
│ File: src/apps/bank_statements/               │
│       gpt_statement_parser.py (~237 lines)    │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│ BankStatementViewSet (views.py)               │
│ → Creates BankStatement + BankTransaction     │
│ → Auto-reconciliation with invoices           │
│                                                │
│ File: src/apps/bank_statements/               │
│       views.py (~849 lines)                   │
│       services/invoice_matcher.py             │
└────────────────────────────────────────────────┘
```

### 2.3 Files Involved (Complete Map)

#### Backend — Invoice Processing

| File                                      | Lines | Purpose                                      |
| ----------------------------------------- | ----- | -------------------------------------------- |
| `src/apps/invoices/invoice_parser.py`     | 2073  | OCR + regex extraction + GPT dispatcher      |
| `src/apps/invoices/gpt_invoice_parser.py` | ~180  | GPT-4 text-based JSON extraction             |
| `src/apps/invoices/views.py`              | 1410  | API views, file upload, model creation       |
| `src/apps/invoices/models.py`             | —     | Invoice, LineItem, Supplier, Customer models |
| `src/apps/invoices/serializers.py`        | —     | DRF serializers for all invoice models       |
| `src/apps/invoices/urls.py`               | —     | API URL routing                              |
| `src/apps/invoices/utils.py`              | —     | Email, PDF generation utilities              |

#### Backend — Bank Statement Processing

| File                                                   | Lines | Purpose                                   |
| ------------------------------------------------------ | ----- | ----------------------------------------- |
| `src/apps/bank_statements/statement_parser.py`         | 267   | File type detection + text extraction     |
| `src/apps/bank_statements/gpt_statement_parser.py`     | 237   | GPT-3.5 text-based transaction extraction |
| `src/apps/bank_statements/views.py`                    | 849   | API views, upload, reconciliation         |
| `src/apps/bank_statements/models.py`                   | —     | BankStatement, BankTransaction models     |
| `src/apps/bank_statements/serializers.py`              | —     | DRF serializers                           |
| `src/apps/bank_statements/utils/transaction_mapper.py` | —     | Category mapping for transactions         |
| `src/apps/bank_statements/services/invoice_matcher.py` | —     | Auto-reconciliation logic                 |

#### Backend — Configuration

| File                               | Purpose                                         |
| ---------------------------------- | ----------------------------------------------- |
| `src/core/settings/base.py`        | `GPT_USE_GPT_4`, `GPT_API_KEY` settings         |
| `src/core/settings/development.py` | Dev-specific overrides                          |
| `src/core/settings/production.py`  | Production config                               |
| `requirements.txt`                 | Python dependencies (pytesseract, openai, etc.) |

#### Frontend — Invoice & Bank Statement UI

| File                                                             | Purpose                                          |
| ---------------------------------------------------------------- | ------------------------------------------------ |
| `src/api/invoices/invoices.js`                                   | API calls: upload, parse, CRUD (352 lines)       |
| `src/api/invoices/bankStatements.js`                             | API calls: upload, parse, reconcile (~370 lines) |
| `src/hooks/invoices/useInvoices.js`                              | React Query hooks for invoices                   |
| `src/hooks/invoices/useBankStatements.js`                        | React Query hooks for bank statements            |
| `src/hooks/useBankStatements.js`                                 | Top-level bank statement hooks                   |
| `src/layouts/pages/invoices/expenditure-invoice/upload-invoice/` | Upload & OCR review UI                           |
| `src/layouts/pages/invoices/expenditure-invoice/bulk-review/`    | Bulk OCR review UI                               |
| `src/layouts/pages/bank-statements/upload-statement/`            | Bank statement upload UI                         |
| `src/layouts/pages/bank-statements/review-statement/`            | Statement review UI                              |
| `src/layouts/pages/bank-statements/bulk-review/`                 | Bulk statement review UI                         |

#### Frontend — PWA Infrastructure (to create)

| File                                 | Purpose                                            |
| ------------------------------------ | -------------------------------------------------- |
| `public/manifest.json`               | Already exists — needs PWA enhancement             |
| `public/index.html`                  | Already exists — needs service worker registration |
| `public/service-worker.js`           | **NEW** — Service worker for offline/caching       |
| `src/service-worker-registration.js` | **NEW** — SW registration logic                    |

---

## 3. AI Provider Comparison

### 3.1 For Invoice & Bank Statement Extraction

| Provider      | Model                 | Approach             | Vision | Price (per 1K docs)     | Accuracy   | Moroccan Support          |
| ------------- | --------------------- | -------------------- | ------ | ----------------------- | ---------- | ------------------------- |
| **Anthropic** | Claude 3.5 Sonnet     | General AI + Vision  | ✅     | ~$15-30                 | ⭐⭐⭐⭐½  | Excellent (French/Arabic) |
| **OpenAI**    | GPT-4o                | General AI + Vision  | ✅     | ~$12-25                 | ⭐⭐⭐⭐   | Good                      |
| **OpenAI**    | GPT-4 (current)       | Text only            | ❌     | ~$30-60                 | ⭐⭐⭐     | Good (text only)          |
| **Google**    | Document AI           | Specialized          | ✅     | ~$10-65                 | ⭐⭐⭐⭐⭐ | Excellent                 |
| **Azure**     | Document Intelligence | Specialized          | ✅     | ~$10-50                 | ⭐⭐⭐⭐⭐ | Excellent                 |
| **Mistral**   | Pixtral Large         | Open-weight + Vision | ✅     | ~$5-15 / Free self-host | ⭐⭐⭐½    | Good                      |
| **Local**     | pytesseract + regex   | OCR + patterns       | ❌     | $0                      | ⭐⭐       | Poor                      |

### 3.2 Recommendation

**Primary: Claude 3.5 Sonnet (Anthropic)** — Best instruction-following for structured JSON, excellent French support, 200K context, vision-capable, competitive pricing.

**Secondary: GPT-4o (OpenAI)** — Already integrated (just need to upgrade from GPT-4 to GPT-4o + add vision). Cheaper and faster than current GPT-4.

**Fallback: Current regex parser** — Zero-cost, handles simple invoices.

### 3.3 Why Vision Over OCR + Text?

| Aspect                | OCR + Text → AI              | AI Vision (Direct)         |
| --------------------- | ---------------------------- | -------------------------- |
| Table structure       | ❌ Lost during OCR           | ✅ AI sees columns/rows    |
| Colored/styled text   | ❌ OCR ignores styling       | ✅ AI reads visual cues    |
| Multi-column layout   | ❌ OCR linearizes text       | ✅ AI understands layout   |
| Handwritten notes     | ❌ Poor OCR accuracy         | ✅ AI can read handwriting |
| Stamps/logos          | ❌ Ignored                   | ✅ AI can identify         |
| Arabic text (Morocco) | ❌ pytesseract poor RTL      | ✅ Native language support |
| Image quality issues  | ❌ Preprocessing required    | ✅ AI handles noise        |
| Dependencies          | pytesseract, poppler, opencv | Only HTTP API calls        |

---

## 4. Phase 1 — Multi-Provider AI Vision Backend (Invoice)

### 4.1 Overview

Create a new `ai_invoice_parser.py` that sends invoice page images directly to vision-capable AI models, bypassing the entire OCR pipeline.

### 4.2 Tasks

#### Task 1.1: Create AI Invoice Parser Module

- **File:** `src/apps/invoices/ai_invoice_parser.py` (NEW)
- **Description:** Multi-provider parser with Claude → GPT-4o → regex fallback chain
- **Features:**
  - Converts PDF/JPG/PNG to base64 images
  - Sends images directly to Claude 3.5 Sonnet vision API
  - Falls back to GPT-4o vision, then regex parser
  - Shared extraction prompt optimized for Moroccan/French invoices
  - JSON response parsing and validation
  - Post-processing (numeric normalization, missing field defaults)
  - Tracks which provider was used via `metadata.parsed_by`
- **Dependencies:** `anthropic` Python package

#### Task 1.2: Add Anthropic API Settings

- **File:** `src/core/settings/base.py`
- **Changes:**
  ```python
  # Add after existing GPT settings (around line 372-373)
  ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
  USE_AI_VISION_PARSER = config('USE_AI_VISION_PARSER', default=True, cast=bool)
  AI_PARSER_PRIMARY = config('AI_PARSER_PRIMARY', default='claude')  # claude | openai | google
  AI_PARSER_TIMEOUT = config('AI_PARSER_TIMEOUT', default=90, cast=int)
  ```

#### Task 1.3: Update Settings Env Files

- **File:** `.env` / `.env.dist`
- **Changes:**
  ```env
  ANTHROPIC_API_KEY=sk-ant-xxx
  USE_AI_VISION_PARSER=True
  AI_PARSER_PRIMARY=claude
  AI_PARSER_TIMEOUT=90
  ```

#### Task 1.4: Update Requirements

- **File:** `requirements.txt`
- **Changes:**

  ```
  anthropic>=0.34.0
  ```

  - Consider adding `google-cloud-documentai` if Google Document AI is desired later

#### Task 1.5: Update Invoice Parser Entry Point

- **File:** `src/apps/invoices/invoice_parser.py`
- **Changes:** Modify `InvoiceParser.parse_invoice()` (around line 112-139) to:
  1. Check `USE_AI_VISION_PARSER` setting
  2. If enabled, delegate to `AIInvoiceParser.parse_invoice()`
  3. Catch exceptions and fall back to legacy pipeline
  4. Keep legacy OCR + GPT/regex path intact as fallback

#### Task 1.6: Update Invoice Views for New Parser

- **File:** `src/apps/invoices/views.py`
- **Changes:**
  - The views already call `InvoiceParser.parse_invoice()` — no changes needed if Task 1.5 is done correctly
  - Add `parsed_by` field logging to response metadata
  - Update batch parsing endpoints to support new parser

#### Task 1.7: Add Parsing Analytics/Logging

- **File:** `src/apps/invoices/models.py`
- **Changes:** Add optional field to track which AI provider parsed each invoice:
  ```python
  # On Invoice model
  parsed_by = models.CharField(max_length=20, blank=True, null=True,
      help_text="AI provider used for parsing: claude, openai, regex")
  ```
- **File:** `src/apps/invoices/serializers.py` — Add `parsed_by` to serializer

#### Task 1.8: Create Migration

- **File:** `src/apps/invoices/migrations/0017_add_parsed_by.py` (auto-generated)
- Run: `python src/manage.py makemigrations invoices`

### 4.3 New File: `ai_invoice_parser.py` — Detailed Design

```
class AIInvoiceParser:
    │
    ├── __init__()
    │   └── Detect available providers from settings
    │
    ├── parse_invoice(invoice_file) → Dict
    │   ├── _file_to_images(file) → List[base64_str]
    │   ├── Try provider chain: claude → openai → regex
    │   ├── _validate_result(data) → bool
    │   └── _post_process(data) → Dict
    │
    ├── _parse_with_claude(images) → Dict
    │   ├── Build Anthropic Messages API request with images
    │   ├── model: "claude-sonnet-4-20250514"
    │   └── Parse JSON response
    │
    ├── _parse_with_openai(images) → Dict
    │   ├── Build OpenAI Chat API request with image_url content
    │   ├── model: "gpt-4o"
    │   └── Parse JSON response
    │
    ├── _parse_json_response(raw_text) → Dict
    │   └── Strip markdown fences, parse JSON
    │
    ├── _validate_result(data) → bool
    │   └── Check: has total OR line_items OR invoice_number
    │
    └── _post_process(data) → Dict
        ├── Normalize numeric fields to float
        ├── Calculate missing totals (subtotal + tax = total)
        ├── Infer tax_rate from amounts
        └── Ensure all required keys exist with defaults
```

### 4.4 Extraction Prompt Design

The shared prompt should handle:

- **Moroccan invoices:** ICE (15 digits), IF, RC, CNSS, TVA 20%, MAD/DH currency, TTC/HT totals
- **French invoices:** SIRET, TVA intra, EUR currency
- **English invoices:** Tax ID, VAT, standard fields
- **Line items:** Description, quantity, unit price, amount, tax per line
- **Both printed and handwritten** annotations
- **Stamps, logos, bank details** (RIB for Morocco)

---

## 5. Phase 2 — Bank Statement AI Vision

### 5.1 Overview

Apply the same vision approach to bank statement parsing. The current pipeline already uses GPT (gpt-3.5-turbo-16k), but only on extracted text.

### 5.2 Tasks

#### Task 2.1: Create AI Statement Parser Module

- **File:** `src/apps/bank_statements/ai_statement_parser.py` (NEW)
- **Description:** Multi-provider vision parser for bank statements
- **Features:**
  - Same provider chain: Claude → GPT-4o → legacy GPT-3.5 text → CSV/Excel parser
  - Specialized prompt for Moroccan bank formats
  - Understands bank-specific table layouts (Attijariwafa, CIH, BMCE, etc.)
  - Extracts: bank name, account details, period, transactions, balances
  - Uses existing `TransactionMapper` for category normalization
- **Reuses:** `utils/transaction_mapper.py`, `services/invoice_matcher.py`

#### Task 2.2: Update Statement Parser Entry Point

- **File:** `src/apps/bank_statements/statement_parser.py`
- **Changes:** Modify `StatementParser.parse_statement()` (line ~22) to:
  1. Check `USE_AI_VISION_PARSER` setting
  2. For PDF/image files: delegate to `AIStatementParser`
  3. For CSV/Excel files: keep existing direct parsing (structured data, no AI needed)
  4. Fall back to legacy GPT text parser on failure

#### Task 2.3: Update Bank Statement Views

- **File:** `src/apps/bank_statements/views.py`
- **Changes:**
  - Add `parsed_by` tracking to upload response
  - No major changes needed if Task 2.2 modifies entry point correctly

#### Task 2.4: Add Parsing Tracking to Model

- **File:** `src/apps/bank_statements/models.py`
- **Changes:** The `parser_used` field already exists on `BankStatement` model (seen in `filterset_fields`). Update to include new providers: `claude`, `openai_vision`, `gpt_text`, `csv_direct`, `regex`.
- **File:** `src/apps/bank_statements/serializers.py` — Ensure `parser_used` is exposed

#### Task 2.5: Statement Prompt Design

- Specialized for Moroccan bank statement formats
- Detects bank from logo/header (Attijariwafa, CIH, BMCE, Banque Populaire, etc.)
- Extracts transaction table with: date, description/libellé, debit, credit, balance
- Handles multi-page statements (send all pages as images)
- Extracts RIB, account number, period dates, opening/closing balance

### 5.3 New File: `ai_statement_parser.py` — Detailed Design

```
class AIStatementParser:
    │
    ├── __init__()
    │   └── Detect available providers, init TransactionMapper
    │
    ├── parse_statement(file) → Dict
    │   ├── Detect file type
    │   ├── If CSV/Excel → delegate to existing parsers (no vision needed)
    │   ├── If PDF/Image → _file_to_images() → Try vision providers
    │   └── Post-process with TransactionMapper
    │
    ├── _parse_with_claude(images) → Dict
    │   └── Bank statement extraction prompt + images
    │
    ├── _parse_with_openai(images) → Dict
    │   └── Same prompt, different API
    │
    └── _post_process(data) → Dict
        ├── Normalize bank_name using existing mapping
        ├── Normalize transaction categories
        ├── Validate opening + transactions = closing balance
        └── Flag suspicious transactions
```

---

## 6. Phase 3 — Frontend PWA Conversion

### 6.1 Overview

Convert the existing React frontend into a Progressive Web App to enable:

- **Install on phone** home screen (Android + iOS)
- **Camera capture** for invoice/statement upload
- **Offline support** for viewing previously loaded data
- **Push notifications** for invoice status changes
- **Background sync** for uploads when connectivity is restored

### 6.2 Current Frontend State

The project already has:

- ✅ `public/manifest.json` (basic — needs enhancement)
- ✅ `<meta name="theme-color">` in `public/index.html`
- ✅ Responsive Material UI components
- ❌ No service worker
- ❌ No offline caching strategy
- ❌ No camera integration
- ❌ No PWA icons (only favicon.png at 64x64)
- ❌ No install prompt handling

### 6.3 Tasks

#### Task 3.1: Enhance manifest.json

- **File:** `public/manifest.json`
- **Changes:**
  ```json
  {
    "short_name": "ComptaGo",
    "name": "ComptaGo - Comptabilité Intelligente",
    "description": "Logiciel de comptabilité et gestion d'entreprise",
    "icons": [
      { "src": "icons/icon-72x72.png", "sizes": "72x72", "type": "image/png" },
      { "src": "icons/icon-96x96.png", "sizes": "96x96", "type": "image/png" },
      {
        "src": "icons/icon-128x128.png",
        "sizes": "128x128",
        "type": "image/png"
      },
      {
        "src": "icons/icon-144x144.png",
        "sizes": "144x144",
        "type": "image/png"
      },
      {
        "src": "icons/icon-152x152.png",
        "sizes": "152x152",
        "type": "image/png"
      },
      {
        "src": "icons/icon-192x192.png",
        "sizes": "192x192",
        "type": "image/png",
        "purpose": "any maskable"
      },
      {
        "src": "icons/icon-384x384.png",
        "sizes": "384x384",
        "type": "image/png"
      },
      {
        "src": "icons/icon-512x512.png",
        "sizes": "512x512",
        "type": "image/png",
        "purpose": "any maskable"
      }
    ],
    "start_url": "/",
    "display": "standalone",
    "orientation": "portrait-primary",
    "theme_color": "#1A73E8",
    "background_color": "#ffffff",
    "categories": ["business", "finance", "productivity"],
    "lang": "fr",
    "scope": "/",
    "prefer_related_applications": false
  }
  ```

#### Task 3.2: Generate PWA Icons

- **Directory:** `public/icons/` (NEW)
- **Action:** Generate all required icon sizes from the existing logo
- Sizes needed: 72, 96, 128, 144, 152, 192, 384, 512
- Include maskable versions for Android adaptive icons
- Tools: Use `sharp` or online generator from source SVG/PNG

#### Task 3.3: Create Service Worker

- **File:** `public/service-worker.js` (NEW)
- **Features:**
  - **Cache-first** strategy for static assets (JS, CSS, images, fonts)
  - **Network-first** strategy for API calls
  - **Stale-while-revalidate** for non-critical assets
  - **Background sync** for failed invoice/statement uploads
  - **Precache** app shell for instant loading
  - Cache versioning for update management

#### Task 3.4: Create Service Worker Registration

- **File:** `src/serviceWorkerRegistration.js` (NEW)
- **Features:**
  - Register SW on app load
  - Handle SW updates (show "New version available" prompt)
  - Handle offline/online events
  - Unregister option for development

#### Task 3.5: Update index.html for PWA

- **File:** `public/index.html`
- **Changes:**
  ```html
  <!-- Add to <head> -->
  <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
  <link rel="apple-touch-icon" href="%PUBLIC_URL%/icons/icon-192x192.png" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="apple-mobile-web-app-title" content="ComptaGo" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="msapplication-TileColor" content="#1A73E8" />
  <meta
    name="msapplication-TileImage"
    content="%PUBLIC_URL%/icons/icon-144x144.png"
  />
  ```

#### Task 3.6: Update App.js for PWA

- **File:** `src/App.js`
- **Changes:**
  - Import and call `serviceWorkerRegistration.register()`
  - Add install prompt handler (BeforeInstallPromptEvent)
  - Add online/offline status context
  - Add update available notification (MDSnackbar)

#### Task 3.7: Create PWA Install Prompt Component

- **File:** `src/components/PWAInstallPrompt/index.js` (NEW)
- **Features:**
  - Detect if app is installable (not already installed)
  - Show install banner/button
  - Handle `beforeinstallprompt` event
  - iOS-specific instructions (iOS doesn't support beforeinstallprompt)
  - Dismiss and don't show again option
  - Multi-language support (French/English via i18next)

#### Task 3.8: Create Offline Indicator Component

- **File:** `src/components/OfflineIndicator/index.js` (NEW)
- **Features:**
  - Show banner when offline
  - Queue actions while offline
  - Show sync status when back online

#### Task 3.9: Add PWA Translations

- **File:** `src/locales/fr/translation.json`
- **File:** `src/locales/en/translation.json`
- **Changes:** Add keys for:
  ```json
  {
    "pwa": {
      "install_title": "Installer ComptaGo",
      "install_description": "Accédez rapidement depuis votre écran d'accueil",
      "install_button": "Installer",
      "install_dismiss": "Plus tard",
      "update_available": "Mise à jour disponible",
      "update_button": "Mettre à jour",
      "offline_message": "Vous êtes hors ligne",
      "sync_pending": "Synchronisation en cours..."
    }
  }
  ```

---

## 7. Phase 4 — Mobile PWA Features

### 7.1 Overview

Once PWA infrastructure is in place, add mobile-first features that leverage device capabilities.

### 7.2 Tasks

#### Task 4.1: Camera Capture for Invoices

- **File:** `src/components/CameraCapture/index.js` (NEW)
- **Features:**
  - Access device camera via `navigator.mediaDevices.getUserMedia()`
  - Live viewfinder with document edge detection guide
  - Capture photo and preview before upload
  - Support front and rear camera switching
  - Flash control for low-light conditions
  - Auto-crop suggestion
- **Integration points:**
  - `src/layouts/pages/invoices/expenditure-invoice/upload-invoice/` — Add camera option
  - `src/layouts/pages/bank-statements/upload-statement/` — Add camera option

#### Task 4.2: Mobile Upload Flow

- **File:** `src/layouts/pages/invoices/expenditure-invoice/upload-invoice/index.js` (MODIFY)
- **File:** `src/layouts/pages/bank-statements/upload-statement/index.js` (MODIFY)
- **Changes:**
  - Add "Take Photo" button alongside "Upload File"
  - Integrate CameraCapture component
  - Support multi-page scanning (take multiple photos for one document)
  - Preview gallery before submission
  - Progress indicator during AI processing
  - On mobile: camera button is primary, upload is secondary
  - On desktop: upload is primary, camera is hidden

#### Task 4.3: Mobile-Optimized Invoice List

- **File:** `src/layouts/pages/invoices/expenditure-invoice/all-invoices/index.js` (MODIFY)
- **File:** `src/layouts/pages/income-invoice/all-invoices/index.js` (MODIFY)
- **Changes:**
  - Responsive card view for mobile (instead of data grid table)
  - Swipe actions (swipe right = mark paid, swipe left = delete)
  - Pull-to-refresh
  - Floating action button for quick invoice creation
  - Bottom navigation on mobile

#### Task 4.4: Mobile-Optimized Bank Statement View

- **File:** `src/layouts/pages/bank-statements/all-statements/index.js` (MODIFY)
- **File:** `src/layouts/pages/bank-statements/view-statement/index.js` (MODIFY)
- **Changes:**
  - Card-based transaction list for mobile
  - Swipe to reconcile
  - Transaction search/filter bottom sheet
  - Sticky header with balance summary

#### Task 4.5: Push Notifications Setup

- **Backend File:** `src/apps/notifications/` (existing app, extend)
- **Frontend File:** `src/firebase-conf/` (existing config, extend)
- **File:** `public/firebase-messaging-sw.js` (NEW)
- **Features:**
  - Firebase Cloud Messaging (FCM) integration (Firebase already in dependencies)
  - Backend sends push when: invoice status changes, payment received, AI processing complete
  - Frontend registers FCM token and sends to backend
  - Handle notification click → deep link to relevant invoice/statement

#### Task 4.6: Background Sync for Uploads

- **File:** `public/service-worker.js` (MODIFY)
- **File:** `src/api/invoices/invoices.js` (MODIFY)
- **File:** `src/api/invoices/bankStatements.js` (MODIFY)
- **Features:**
  - When offline, queue upload in IndexedDB
  - Service worker registers `sync` event
  - When back online, automatically retry uploads
  - Show progress for queued uploads

#### Task 4.7: Mobile Dashboard

- **File:** `src/layouts/dashboards/index.js` (MODIFY)
- **Changes:**
  - Stacked card layout on mobile (instead of grid)
  - Quick action buttons: Scan Invoice, Upload Statement, View Reports
  - Swipeable chart cards
  - Key metrics at top (Revenue, Expenses, Balance)

### 7.3 Responsive Breakpoints Strategy

```
Mobile:    < 600px   → Card views, bottom nav, camera-first
Tablet:    600-960px → Hybrid layout, side nav collapsed
Desktop:   > 960px   → Current layout (data grids, full sidenav)
```

Leverage existing MUI breakpoints:

```javascript
// Already available via @mui/material
const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
const isTablet = useMediaQuery(theme.breakpoints.between("sm", "md"));
```

---

## 8. Phase 5 — Testing & QA

### 8.1 Backend Testing

#### Task 5.1: AI Parser Unit Tests

- **File:** `src/apps/invoices/tests/test_ai_invoice_parser.py` (NEW)
- **Tests:**
  - Mock Claude API response → verify JSON parsing
  - Mock GPT-4o API response → verify JSON parsing
  - Test fallback chain (Claude fails → GPT-4o → regex)
  - Test image conversion (PDF → base64, JPG → base64)
  - Test post-processing (numeric normalization, missing fields)
  - Test validation logic (minimum required fields)
  - Test with real sample invoices from `invoices_sample/`

#### Task 5.2: AI Statement Parser Tests

- **File:** `src/apps/bank_statements/tests/test_ai_statement_parser.py` (NEW)
- **Tests:**
  - Same pattern as invoice tests
  - Test Moroccan bank name detection
  - Test transaction categorization
  - Test CSV/Excel bypass (no AI for structured formats)

#### Task 5.3: Integration Tests

- **File:** `src/apps/invoices/tests/test_invoice_upload_integration.py` (NEW)
- **Tests:**
  - Full upload → parse → create flow with mocked AI
  - Verify Invoice + LineItem models created correctly
  - Verify Supplier/Customer matching
  - Test concurrent uploads

#### Task 5.4: Performance Benchmark

- **File:** `src/apps/invoices/tests/test_parser_benchmark.py` (NEW)
- **Tests:**
  - Compare regex vs GPT-4 text vs Claude vision vs GPT-4o vision
  - Measure: accuracy, time, cost per invoice
  - Use sample invoices from `invoices_sample/` directory
  - Generate comparison report

### 8.2 Frontend Testing

#### Task 5.5: PWA Audit

- Run Lighthouse PWA audit → target score > 90
- Test offline functionality
- Test install flow on Android Chrome, iOS Safari, Desktop Chrome/Edge
- Test camera capture on multiple devices

#### Task 5.6: Mobile Responsiveness Tests

- Test all invoice pages at 360px, 390px, 414px widths
- Test bank statement pages at same widths
- Test dashboard at same widths
- Verify touch targets are at least 44x44px

---

## 9. Phase 6 — Deployment & Rollout

### 9.1 Tasks

#### Task 6.1: Environment Variables Setup

- **Railway/Hosting:** Add `ANTHROPIC_API_KEY`, `USE_AI_VISION_PARSER`, `AI_PARSER_PRIMARY` to production environment
- **Development:** Update `.env.dist` with all new variables

#### Task 6.2: Database Migration

- Run `python src/manage.py migrate` for `parsed_by` field on Invoice model
- Verify with: `python src/manage.py showmigrations invoices`

#### Task 6.3: Dependency Installation

- Backend: `pip install anthropic>=0.34.0`
- Frontend: `npm install workbox-webpack-plugin` (if using Workbox for SW)
- Verify: `pip freeze | grep anthropic`

#### Task 6.4: Feature Flag Rollout

- Enable `USE_AI_VISION_PARSER=False` initially in production
- Test with internal team using specific invoices
- Monitor: accuracy, latency, cost via Django logging
- Gradually enable: 10% → 50% → 100% of requests

#### Task 6.5: Monitoring & Alerts

- Log all AI parser calls with provider, latency, success/failure
- Alert on: >5% failure rate, latency >15s, API key quota near limit
- Dashboard: parsing stats by provider (in Django admin or custom endpoint)

#### Task 6.6: PWA Deployment

- Verify HTTPS is configured (required for service workers)
- Set correct `Cache-Control` headers for SW file (no-cache)
- Test install flow on production domain
- Submit to PWA stores if desired (Microsoft Store, Google Play via TWA)

---

## 10. File Reference Map

### Complete list of files to CREATE (new)

| #   | File                                                         | Phase   | Description                                 |
| --- | ------------------------------------------------------------ | ------- | ------------------------------------------- |
| 1   | `src/apps/invoices/ai_invoice_parser.py`                     | Phase 1 | Multi-provider vision parser for invoices   |
| 2   | `src/apps/bank_statements/ai_statement_parser.py`            | Phase 2 | Multi-provider vision parser for statements |
| 3   | `src/apps/invoices/tests/test_ai_invoice_parser.py`          | Phase 5 | Unit tests for AI invoice parser            |
| 4   | `src/apps/bank_statements/tests/test_ai_statement_parser.py` | Phase 5 | Unit tests for AI statement parser          |
| 5   | `src/apps/invoices/tests/test_invoice_upload_integration.py` | Phase 5 | Integration tests                           |
| 6   | `src/apps/invoices/tests/test_parser_benchmark.py`           | Phase 5 | Performance benchmark tests                 |
| 7   | `public/service-worker.js` (frontend)                        | Phase 3 | Service worker (caching, offline, sync)     |
| 8   | `src/serviceWorkerRegistration.js` (frontend)                | Phase 3 | SW registration logic                       |
| 9   | `src/components/PWAInstallPrompt/index.js` (frontend)        | Phase 3 | Install prompt component                    |
| 10  | `src/components/OfflineIndicator/index.js` (frontend)        | Phase 3 | Offline status indicator                    |
| 11  | `src/components/CameraCapture/index.js` (frontend)           | Phase 4 | Camera capture component                    |
| 12  | `public/icons/` (frontend)                                   | Phase 3 | PWA icons (8 sizes)                         |
| 13  | `public/firebase-messaging-sw.js` (frontend)                 | Phase 4 | FCM service worker                          |

### Complete list of files to MODIFY (existing)

| #   | File                                                                        | Phase   | Changes                                              |
| --- | --------------------------------------------------------------------------- | ------- | ---------------------------------------------------- |
| 1   | `src/core/settings/base.py`                                                 | Phase 1 | Add ANTHROPIC_API_KEY, USE_AI_VISION_PARSER settings |
| 2   | `requirements.txt`                                                          | Phase 1 | Add `anthropic>=0.34.0`                              |
| 3   | `src/apps/invoices/invoice_parser.py`                                       | Phase 1 | Update parse_invoice() entry point                   |
| 4   | `src/apps/invoices/views.py`                                                | Phase 1 | Add parsed_by tracking                               |
| 5   | `src/apps/invoices/models.py`                                               | Phase 1 | Add parsed_by field                                  |
| 6   | `src/apps/invoices/serializers.py`                                          | Phase 1 | Expose parsed_by                                     |
| 7   | `src/apps/bank_statements/statement_parser.py`                              | Phase 2 | Update parse_statement() entry point                 |
| 8   | `src/apps/bank_statements/views.py`                                         | Phase 2 | Add parsed_by tracking                               |
| 9   | `public/manifest.json` (frontend)                                           | Phase 3 | Full PWA manifest                                    |
| 10  | `public/index.html` (frontend)                                              | Phase 3 | PWA meta tags, SW registration                       |
| 11  | `src/App.js` (frontend)                                                     | Phase 3 | SW registration, install prompt                      |
| 12  | `src/locales/fr/translation.json` (frontend)                                | Phase 3 | PWA translations                                     |
| 13  | `src/locales/en/translation.json` (frontend)                                | Phase 3 | PWA translations                                     |
| 14  | `src/layouts/pages/invoices/expenditure-invoice/upload-invoice/` (frontend) | Phase 4 | Camera capture integration                           |
| 15  | `src/layouts/pages/bank-statements/upload-statement/` (frontend)            | Phase 4 | Camera capture integration                           |
| 16  | `src/layouts/pages/invoices/*/all-invoices/` (frontend)                     | Phase 4 | Mobile responsive views                              |
| 17  | `src/layouts/pages/bank-statements/all-statements/` (frontend)              | Phase 4 | Mobile responsive views                              |
| 18  | `src/layouts/dashboards/index.js` (frontend)                                | Phase 4 | Mobile dashboard layout                              |
| 19  | `src/api/invoices/invoices.js` (frontend)                                   | Phase 4 | Background sync support                              |
| 20  | `src/api/invoices/bankStatements.js` (frontend)                             | Phase 4 | Background sync support                              |

### Files to DEPRECATE (eventually remove)

| #   | File                                               | When                                    | Reason                             |
| --- | -------------------------------------------------- | --------------------------------------- | ---------------------------------- |
| 1   | `src/apps/invoices/gpt_invoice_parser.py`          | After Phase 1 stable                    | Replaced by ai_invoice_parser.py   |
| 2   | `src/apps/bank_statements/gpt_statement_parser.py` | After Phase 2 stable                    | Replaced by ai_statement_parser.py |
| 3   | Regex patterns in `invoice_parser.py`              | After Phase 1 stable (keep as fallback) | Vision models handle extraction    |

---

## 11. Risk Assessment

| Risk                              | Probability | Impact | Mitigation                                                     |
| --------------------------------- | ----------- | ------ | -------------------------------------------------------------- |
| Claude API downtime               | Low         | High   | GPT-4o fallback + regex fallback chain                         |
| AI hallucinations (wrong numbers) | Medium      | High   | Post-processing validation, human review UI                    |
| High API costs at scale           | Medium      | Medium | Caching, rate limiting, use cheaper models for simple invoices |
| PWA not supported on old iOS      | Low         | Low    | Graceful degradation, app still works in browser               |
| Camera quality too low for AI     | Medium      | Medium | Image quality guide for users, allow retake                    |
| Service worker caching bugs       | Medium      | Medium | Cache versioning, force-update mechanism                       |
| Migration breaks existing flow    | Low         | High   | Feature flags, gradual rollout, keep legacy code               |

---

## 12. Timeline

```
Week 1-2:   Phase 1 — AI Vision Invoice Parser (backend)
            ├─ Task 1.1: Create ai_invoice_parser.py
            ├─ Task 1.2-1.4: Settings, env, requirements
            ├─ Task 1.5: Update invoice_parser.py entry point
            ├─ Task 1.6-1.8: Views, models, migration
            └─ Internal testing with sample invoices

Week 3:     Phase 2 — AI Vision Bank Statement Parser (backend)
            ├─ Task 2.1: Create ai_statement_parser.py
            ├─ Task 2.2-2.4: Update entry point, views, models
            └─ Internal testing with sample statements

Week 4-5:   Phase 3 — PWA Conversion (frontend)
            ├─ Task 3.1-3.2: Manifest, icons
            ├─ Task 3.3-3.4: Service worker, registration
            ├─ Task 3.5-3.6: HTML updates, App.js
            ├─ Task 3.7-3.8: Install prompt, offline indicator
            └─ Task 3.9: Translations

Week 6-7:   Phase 4 — Mobile Features (frontend)
            ├─ Task 4.1-4.2: Camera capture, mobile upload
            ├─ Task 4.3-4.4: Mobile invoice/statement views
            ├─ Task 4.5: Push notifications
            ├─ Task 4.6: Background sync
            └─ Task 4.7: Mobile dashboard

Week 8:     Phase 5 — Testing & QA
            ├─ Task 5.1-5.4: Backend tests, benchmarks
            └─ Task 5.5-5.6: PWA audit, mobile testing

Week 9:     Phase 6 — Deployment & Rollout
            ├─ Task 6.1-6.3: Environment, migrations, dependencies
            ├─ Task 6.4: Feature flag rollout (10% → 50% → 100%)
            ├─ Task 6.5: Monitoring setup
            └─ Task 6.6: PWA deployment

Total: ~9 weeks
```

---

## Appendix A: Package Versions

### Backend (Python)

```
anthropic>=0.34.0          # Claude API client
openai>=1.0.0              # Already installed — upgrade for GPT-4o vision
pytesseract                # Keep for regex fallback
pdf2image                  # Keep for image conversion
opencv-python-headless     # Keep for regex fallback preprocessing
pdfplumber                 # Keep for bank statement text extraction
```

### Frontend (npm)

```
workbox-webpack-plugin     # Service worker tooling (optional, can write raw SW)
web-push                   # Push notification utilities (optional)
idb                        # IndexedDB wrapper for offline storage
```

---

## Appendix B: Environment Variables Reference

| Variable                 | Default  | Description                                       |
| ------------------------ | -------- | ------------------------------------------------- |
| `OPENAI_API_KEY`         | `''`     | OpenAI API key (existing)                         |
| `USE_GPT_INVOICE_PARSER` | `False`  | Legacy GPT-4 text parser toggle (existing)        |
| `ANTHROPIC_API_KEY`      | `''`     | Anthropic Claude API key (NEW)                    |
| `USE_AI_VISION_PARSER`   | `True`   | Enable vision-based parsing (NEW)                 |
| `AI_PARSER_PRIMARY`      | `claude` | Primary AI provider: claude, openai, google (NEW) |
| `AI_PARSER_TIMEOUT`      | `90`     | AI API call timeout in seconds (NEW)              |

---

## Appendix C: API Response Schema Changes

### Invoice Parse Response — New `metadata` field

```json
{
  "invoice_number": "FA-2026-001",
  "metadata": {
    "language": "fr",
    "country": "MA",
    "template": "standard",
    "parsed_by": "claude", // NEW
    "parse_time_ms": 3200, // NEW
    "confidence": 0.95 // NEW (provider-dependent)
  }
}
```

### Bank Statement Parse Response — Updated `parser_used`

```json
{
  "bank_name": "ATTIJARIWAFA_BANK",
  "parser_used": "claude_vision",    // Updated: was "gpt" or "traditional"
  "transactions": [...]
}
```
