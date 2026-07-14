#!/usr/bin/env python3
import os
import re
import csv

ROOT = os.path.dirname(os.path.dirname(__file__))
TARGET = os.path.join(ROOT, 'inventory')
PATTERNS = [
    r"\.save\(",
    r"objects\.create\(",
    r"update_or_create\(",
    r"cursor\.execute\(",
    r"\.delete\(",
    r"bulk_create\(",
    r"\.update\(",
]
COMPILED = re.compile('|'.join('(%s)' % p for p in PATTERNS))

CSV_PATH = os.path.join(ROOT, 'approval_audit_detailed.csv')


def find_enclosing_def(lines, idx):
    # search upwards for def or class
    for i in range(idx, max(-1, idx-200), -1):
        line = lines[i].strip()
        m = re.match(r'def\s+([a-zA-Z0-9_]+)\s*\(', line)
        if m:
            return m.group(1), i+1
        m2 = re.match(r'class\s+([A-Za-z0-9_]+)\s*\(?', line)
        if m2:
            return 'class:' + m2.group(1), i+1
    return '(module)', 1


def extract_model_from_snippet(snippet):
    # best-effort: look for Pattern: X.objects.create or Tape.objects.update_or_create
    m = re.search(r"([A-Za-z0-9_]+)\.objects\.(create|update_or_create|filter|get|bulk_create)", snippet)
    if m:
        return m.group(1)
    # for assignment like "tape = Tape.objects.create"
    m2 = re.search(r"([A-Za-z0-9_]+)\s*=\s*([A-Za-z0-9_]+)\.objects\.(create|update_or_create)", snippet)
    if m2:
        return m2.group(2)
    # for variable.save(), try to find var assignment above (simple heuristic)
    m3 = re.search(r"([A-Za-z0-9_]+)\.save\(", snippet)
    if m3:
        var = m3.group(1)
        # return var as unknown-model:var
        return f'var:{var}'
    return ''


def classify_operation(snippet):
    s = snippet
    if 'objects.create(' in s:
        return 'Create'
    if 'update_or_create(' in s:
        return 'Create/Update'
    if '.save(' in s:
        return 'Save (Create/Update)'
    if '.delete(' in s:
        return 'Delete'
    if 'cursor.execute(' in s:
        return 'Raw SQL / Schema'
    if '.update(' in s:
        return 'Bulk Update'
    if 'bulk_create(' in s:
        return 'Bulk Create'
    return 'Unknown'


def risk_level_for_model(model_name):
    if not model_name:
        return 'Medium'
    k = model_name.lower()
    if any(x in k for x in ('tape', 'shipment', 'reconciliation', 'role', 'user', 'exception', 'branch', 'import', 'schema')):
        return 'Critical' if any(x in k for x in ('tape', 'shipment', 'role', 'user', 'schema')) else 'High'
    return 'Medium'


rows = []
for dirpath, dirnames, filenames in os.walk(TARGET):
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if COMPILED.search(line):
                fn_name, def_line = find_enclosing_def(lines, i)
                snippet = line.strip()
                # include some surrounding lines
                context = ''.join(lines[max(0, i-3):min(len(lines), i+3)]).strip().replace('\n', ' || ')
                model = extract_model_from_snippet(context)
                op_type = classify_operation(context)
                creates_pa = 'PendingApproval' in context or 'create_pending_approval' in context
                bypasses = 'No' if creates_pa else 'Yes'
                risk = risk_level_for_model(model)
                deps = []
                if 'AuditLog' in context:
                    deps.append('AuditLog')
                if 'send_mail' in context or 'send_courier_profile_email_alert' in context:
                    deps.append('Email')
                if 'SchemaChangeLog' in context or 'cursor.execute' in context:
                    deps.append('Schema/SQL')
                estimate = 'High' if risk in ('Critical', 'High') else 'Medium'
                recommended = "Wrap write in create_pending_approval(...), include request_payload, requested_changes, related_model and related_object_id. Leave UI/forms intact; replace commit path."
                rows.append({
                    'Module': 'inventory',
                    'File': rel.replace('\\', '/'),
                    'Function/Method': fn_name,
                    'Line Number': i+1,
                    'Model Affected': model,
                    'Operation Type': op_type,
                    'Current Execution Path': context,
                    'Creates PendingApproval': 'Yes' if creates_pa else 'No',
                    'Bypasses Approval Engine': bypasses,
                    'Risk Level': risk,
                    'Recommended Refactor': recommended,
                    'Dependencies': ','.join(deps) or '-',
                    'Estimated Impact': estimate,
                })

# write CSV
with open(CSV_PATH, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['Module','File','Function/Method','Line Number','Model Affected','Operation Type','Current Execution Path','Creates PendingApproval','Bypasses Approval Engine','Risk Level','Recommended Refactor','Dependencies','Estimated Impact']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f'Wrote {len(rows)} entries to {CSV_PATH}')
