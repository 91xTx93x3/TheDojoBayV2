"""Flask application for Dojobay - Public Dojo Directory."""
from flask import Flask, render_template, jsonify, send_from_directory, request, session, redirect, url_for
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

from config import (
    DEFAULT_PROXIES, CACHE_FILE, DOJOS_DATA_FILE,
    CACHE_DURATION, REQUEST_TIMEOUT, HOST, PORT, DEBUG,
    SECRET_KEY, SUBMISSIONS_FILE, AUTH47_CALLBACK_URL,
)
from auth47 import (
    generate_challenge, get_challenge, verify_signature,
    complete_challenge, consume_challenge, generate_qr_png_b64,
)
from cache import StatusCache
from checker import DojoChecker
from data_loader import DojoDataLoader
from background_checker import BackgroundChecker
from bip47_verify import verify_pairing_signature, derive_notification_address


# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize components
data_loader = DojoDataLoader(DOJOS_DATA_FILE)
mainnet_dojos, testnet_dojos = data_loader.load()

cache = StatusCache(CACHE_FILE, CACHE_DURATION)
checker = DojoChecker(DEFAULT_PROXIES, REQUEST_TIMEOUT)

background_checker = BackgroundChecker(
    checker=checker,
    cache=cache,
    mainnet_dojos=mainnet_dojos,
    testnet_dojos=testnet_dojos,
    check_interval=CACHE_DURATION
)


# Context processor for prison days
@app.context_processor
def inject_prison_days():
    """Calculate days Keonne and Bill have been in prison and days remaining."""
    today = datetime.now()
    
    # Keonne's sentence
    keonne_sentence_start = datetime(2025, 12, 19)
    keonne_sentence_end = datetime(2030, 12, 19)  # 5 years later
    keonne_days_served = (today - keonne_sentence_start).days
    keonne_days_remaining = (keonne_sentence_end - today).days
    
    # Bill's sentence
    bill_sentence_start = datetime(2026, 1, 2)
    bill_sentence_end = datetime(2030, 1, 2)  # 4 years later
    bill_days_served = (today - bill_sentence_start).days
    bill_days_remaining = (bill_sentence_end - today).days
    
    # Ensure we don't show negative values
    if keonne_days_served < 0:
        keonne_days_served = 0
    if keonne_days_remaining < 0:
        keonne_days_remaining = 0
    if bill_days_served < 0:
        bill_days_served = 0
    if bill_days_remaining < 0:
        bill_days_remaining = 0
    
    return dict(
        keonne_days_served=keonne_days_served,
        keonne_days_remaining=keonne_days_remaining,
        bill_days_served=bill_days_served,
        bill_days_remaining=bill_days_remaining
    )


ADMIN_PAYNMS = {
    'PM8TJQwkgoVeogzAQe431Bn3FSsXiCqjmFCpysFuSTjB7FaxfrJGtMAEfsA5dvptjMAAxLXKM6bDAen5tFp326EHBmRH6jQ9vJDPnSwARLmUcJoucQtd',  # classic
    'PM8TJQwkgoVeogzAQe431Bn3FSsXiCqjmFCpysFuSTjB7FaxfrJGtMAEfsA5dvptjMAAxLXKM6bDAen5tFp326EHBmRH6jQ9vJDPnSwARLmUcJw9Rtf9',  # segwit
    'PM8TJfHaHuh5xgKoEbrkWaBtytb8qrRNYdmHzxiFcvacD6HpyyxvSV3VLKYsr6UvMxB4jvJP4xxNvCp2pRY3cJPNmLB2L8nYEttaFVszXSBjXNWs3Xj8',  # +max classic
    'PM8TJfHaHuh5xgKoEbrkWaBtytb8qrRNYdmHzxiFcvacD6HpyyxvSV3VLKYsr6UvMxB4jvJP4xxNvCp2pRY3cJPNmLB2L8nYEttaFVszXSBjXNMy8cD9',  # +max segwit
    'PM8TJM51x2mDd85CzEgVc2y7vdyB3eBj93JVjVtCt6PZtmfzhFzYPMXYBXh28zthWhVKGjVQZPT1MKxGxEtfenLYEkuc5GhoWtMzQCF8c8mrckYFM7r1',  # +linkinparkrulz classic
    'PM8TJM51x2mDd85CzEgVc2y7vdyB3eBj93JVjVtCt6PZtmfzhFzYPMXYBXh28zthWhVKGjVQZPT1MKxGxEtfenLYEkuc5GhoWtMzQCF8c8mrckZwnvqs',  # +linkinparkrulz segwit
}


def _resolve_paynym_alias(payment_code):
    """Resolve a BIP47 payment code to a PayNym alias via paynym.rs.
    Returns the alias string (e.g. '+arkad') or None on failure."""
    if not (payment_code and payment_code.startswith('PM8T')):
        return None
    try:
        import urllib.request, ssl
        req_data = json.dumps({'nym': payment_code}).encode()
        req = urllib.request.Request(
            'https://paynym.rs/api/v1/nym',
            data=req_data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            info = json.loads(resp.read())
        nym_name = info.get('nymName') or info.get('nym_name')
        if nym_name:
            return f'+{nym_name}' if not nym_name.startswith('+') else nym_name
    except Exception:
        pass
    return None


@app.context_processor
def inject_session_paynym():
    """Expose logged-in PayNym and avatar URL to all templates."""
    paynym = session.get('paynym')
    avatar_url = f'https://paynym.rs/{paynym}/avatar' if paynym else None
    return dict(
        session_paynym=paynym,
        session_paynym_avatar=avatar_url,
        is_admin=(paynym in ADMIN_PAYNMS),
    )


# Routes
@app.route('/')
def index():
    """Main page with live Dojo status."""
    cached = cache.get()
    if cached:
        return render_template('index.html', status=cached)
    
    # No cache available, return empty state - JS will fetch via API
    from datetime import datetime
    empty_status = {
        "mainnet": [],
        "testnet": [],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "mainnet_active": 0,
            "mainnet_total": len(mainnet_dojos),
            "testnet_active": 0,
            "testnet_total": len(testnet_dojos)
        }
    }
    return render_template('index.html', status=empty_status)


@app.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@app.route('/disclaimer')
def disclaimer():
    """Disclaimer page."""
    return render_template('disclaimer.html')


@app.route('/faq')
def faq():
    """FAQ page."""
    return render_template('faq.html')


# ── Image upload helper ──────────────────────────────────────────────────────

DOJO_IMAGE_DIR = Path(__file__).parent / 'static' / 'images' / 'dojos'
DOJO_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
MAX_IMAGE_BYTES = 1 * 1024 * 1024  # 1 MB
ALLOWED_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}


def _save_dojo_image(file_storage, old_filename=None) -> str | None:
    """Validate and save an uploaded image. Returns filename or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTS:
        return None
    data = file_storage.read()
    if len(data) > MAX_IMAGE_BYTES:
        return None
    filename = f"dojo_{uuid.uuid4().hex}.{ext}"
    (DOJO_IMAGE_DIR / filename).write_bytes(data)
    # Remove old image if replaced
    if old_filename:
        old_path = DOJO_IMAGE_DIR / old_filename
        if old_path.exists():
            old_path.unlink()
    return filename


# ── Dojo self-service helpers ─────────────────────────────────────────────────

def _load_submissions():
    if SUBMISSIONS_FILE.exists():
        with open(SUBMISSIONS_FILE) as f:
            return json.load(f)
    return []


def _save_submissions(data):
    with open(SUBMISSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _require_login():
    """Return paynym from session or None if not logged in."""
    return session.get('paynym')


# ── Dojo self-service routes ──────────────────────────────────────────────────

@app.route('/add-dojo')
def add_dojo():
    """Login page — authenticate via Auth47 / PayNym BIP47."""
    if _require_login():
        return redirect(url_for('dojo_dashboard'))
    return render_template('add_dojo.html')


# ── Auth47 API endpoints (used by JS and wallet) ──────────────────────────────

@app.route('/api/auth47/challenge', methods=['POST'])
def api_auth47_challenge():
    """Generate a new Auth47 challenge; called by the browser on page load."""
    challenge = generate_challenge(AUTH47_CALLBACK_URL)
    return jsonify(challenge.to_dict())


@app.route('/api/auth47/verify', methods=['POST'])
def api_auth47_verify():
    """Wallet callback: verify BIP-137 signature and mark challenge completed."""
    import re

    # Accept JSON or form-encoded body
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    # Wallet sends: challenge (full auth47 URI), nym (payment code), signature
    # Extract nonce from challenge URI: auth47://<nonce>?...
    challenge_uri = str(data.get('challenge') or '')
    m = re.match(r'auth47://([a-f0-9A-F]+)', challenge_uri)
    nonce_from_uri = m.group(1) if m else ''

    challenge_id = str(data.get('challenge_id') or data.get('nonce') or nonce_from_uri).strip()
    payment_code = str(data.get('nym') or data.get('payment_code') or data.get('paynym') or '').strip()
    signature    = str(data.get('signature') or data.get('sig') or '').strip()

    if verify_signature(challenge_id, payment_code, signature):
        complete_challenge(challenge_id, payment_code)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Invalid signature or expired challenge'}), 400


@app.route('/api/auth47/challenge-status/<challenge_id>')
def api_auth47_status(challenge_id):
    """Browser polls this to know when the wallet has signed."""
    ch = get_challenge(challenge_id)
    if not ch:
        return jsonify({'status': 'expired'})
    if ch.completed:
        return jsonify({'status': 'completed'})
    return jsonify({'status': 'pending', 'seconds_remaining': ch.seconds_remaining()})


@app.route('/api/auth47/finalize', methods=['POST'])
def api_auth47_finalize():
    """Browser exchanges a completed challenge_id for a Flask session."""
    data = request.get_json(silent=True) or {}
    challenge_id = str(data.get('challenge_id', '')).strip()
    payment_code = consume_challenge(challenge_id)
    if payment_code:
        session['paynym'] = payment_code
        return jsonify({'ok': True, 'redirect_url': url_for('dojo_dashboard')})
    return jsonify({'ok': False, 'error': 'Challenge not completed or already used'}), 400


@app.route('/add-dojo/logout')
def dojo_logout():
    """Clear session."""
    session.pop('paynym', None)
    return redirect(url_for('add_dojo'))


@app.route('/add-dojo/dashboard')
def dojo_dashboard():
    """Show all dojos registered by the logged-in PayNym."""
    paynym = _require_login()
    if not paynym:
        return redirect(url_for('add_dojo'))
    submissions = _load_submissions()
    user_dojos = [d for d in submissions if d.get('paynym') == paynym]
    return render_template('dojo_dashboard.html', dojos=user_dojos, paynym=paynym)


@app.route('/add-dojo/new', methods=['GET', 'POST'])
def dojo_new():
    """Add a new dojo."""
    paynym = _require_login()
    if not paynym:
        return redirect(url_for('add_dojo'))
    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        pairing_details = request.form.get('pairing_details', '').strip().replace('\r\n', '\n').replace('\r', '\n')
        pairing_signature = request.form.get('pairing_signature', '').strip()
        if not name:
            return render_template('dojo_form.html', mode='new',
                                   error='Dojo name is required.',
                                   form_data=request.form)
        if not pairing_details:
            return render_template('dojo_form.html', mode='new',
                                   error='Pairing details are required.',
                                   form_data=request.form)
        if not pairing_signature:
            return render_template('dojo_form.html', mode='new',
                                   error='Ownership proof (signature) is required.',
                                   form_data=request.form)
        if not verify_pairing_signature(paynym, pairing_details, pairing_signature):
            return render_template('dojo_form.html', mode='new',
                                   error='Signature verification failed. Please sign the exact pairing details with your notification address.',
                                   form_data=request.form)
        image_file = _save_dojo_image(request.files.get('image'))
        entry = {
            'id': str(uuid.uuid4()),
            'paynym': paynym,
            'paynym_alias': _resolve_paynym_alias(paynym),
            'name': name,
            'network': request.form.get('network', 'mainnet').strip(),
            'jurisdiction': request.form.get('jurisdiction', '').strip(),
            'hardware': request.form.get('hardware', '').strip(),
            'nostr_x': request.form.get('nostr_x', '').strip(),
            'pairing_details': pairing_details,
            'pairing_signature': pairing_signature,
            'electrum_server': request.form.get('electrum_server', '').strip(),
            'image_file': image_file,
            'submitted_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'status': 'pending',
        }
        submissions = _load_submissions()
        submissions.append(entry)
        _save_submissions(submissions)
        return redirect(url_for('dojo_dashboard'))
    return render_template('dojo_form.html', mode='new')


@app.route('/add-dojo/edit/<dojo_id>', methods=['GET', 'POST'])
def dojo_edit(dojo_id):
    """Edit an existing dojo (owner only)."""
    paynym = _require_login()
    if not paynym:
        return redirect(url_for('add_dojo'))
    submissions = _load_submissions()
    dojo = next((d for d in submissions
                 if d.get('id') == dojo_id and d.get('paynym') == paynym), None)
    if not dojo:
        return redirect(url_for('dojo_dashboard'))
    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        pairing_details = request.form.get('pairing_details', '').strip().replace('\r\n', '\n').replace('\r', '\n')
        pairing_signature = request.form.get('pairing_signature', '').strip()
        if not name:
            return render_template('dojo_form.html', mode='edit', dojo=dojo,
                                   error='Dojo name is required.',
                                   form_data=request.form)
        if not pairing_details:
            return render_template('dojo_form.html', mode='edit', dojo=dojo,
                                   error='Pairing details are required.',
                                   form_data=request.form)
        if not pairing_signature:
            return render_template('dojo_form.html', mode='edit', dojo=dojo,
                                   error='Ownership proof (signature) is required.',
                                   form_data=request.form)
        if not verify_pairing_signature(paynym, pairing_details, pairing_signature):
            return render_template('dojo_form.html', mode='edit', dojo=dojo,
                                   error='Signature verification failed. Please sign the exact pairing details with your notification address.',
                                   form_data=request.form)
        new_image = _save_dojo_image(request.files.get('image'), dojo.get('image_file'))
        was_approved = dojo.get('status') == 'approved'
        old_name     = dojo.get('name', '')
        dojo['name']           = name
        dojo['network']        = request.form.get('network', 'mainnet').strip()
        dojo['jurisdiction']   = request.form.get('jurisdiction', '').strip()
        dojo['hardware']       = request.form.get('hardware', '').strip()
        dojo['nostr_x']        = request.form.get('nostr_x', '').strip()
        dojo['pairing_details'] = pairing_details
        dojo['pairing_signature'] = pairing_signature
        dojo['electrum_server'] = request.form.get('electrum_server', '').strip()
        if not dojo.get('paynym_alias'):
            dojo['paynym_alias'] = _resolve_paynym_alias(dojo.get('paynym', ''))
        if new_image:
            dojo['image_file'] = new_image
        dojo['updated_at'] = datetime.now().isoformat()
        # If previously approved, revoke from live directory and require re-approval
        if was_approved:
            dojo['status'] = 'pending'
            network  = dojo.get('network', 'mainnet')
            with open(DOJOS_DATA_FILE) as f:
                dojos_data = json.load(f)
            dojos_data[network] = [
                d for d in dojos_data.get(network, []) if d.get('name') != old_name
            ]
            with open(DOJOS_DATA_FILE, 'w') as f:
                json.dump(dojos_data, f, indent=2, ensure_ascii=False)
            global mainnet_dojos, testnet_dojos
            mainnet_dojos, testnet_dojos = data_loader.load()
            background_checker.mainnet_dojos = mainnet_dojos
            background_checker.testnet_dojos = testnet_dojos
            cache.invalidate()
        _save_submissions(submissions)
        return redirect(url_for('dojo_dashboard'))
    return render_template('dojo_form.html', mode='edit', dojo=dojo)


@app.route('/add-dojo/delete/<dojo_id>', methods=['POST'])
def dojo_delete(dojo_id):
    """Delete a dojo (owner only) — marks as deleted for deferred cleanup."""
    paynym = _require_login()
    if not paynym:
        return redirect(url_for('add_dojo'))
    submissions = _load_submissions()
    dojo = next((d for d in submissions
                 if d.get('id') == dojo_id and d.get('paynym') == paynym), None)
    if dojo:
        was_approved = dojo.get('status') == 'approved'
        dojo['status']     = 'deleted'
        dojo['updated_at'] = datetime.now().isoformat()
        # If the dojo was live, remove it from dojos_data.json immediately
        if was_approved:
            network = dojo.get('network', 'mainnet')
            name    = dojo.get('name', '')
            with open(DOJOS_DATA_FILE) as f:
                dojos_data = json.load(f)
            before = len(dojos_data.get(network, []))
            dojos_data[network] = [
                d for d in dojos_data.get(network, [])
                if d.get('name') != name
            ]
            if len(dojos_data[network]) < before:
                with open(DOJOS_DATA_FILE, 'w') as f:
                    json.dump(dojos_data, f, indent=2, ensure_ascii=False)
            global mainnet_dojos, testnet_dojos
            mainnet_dojos, testnet_dojos = data_loader.load()
            background_checker.mainnet_dojos = mainnet_dojos
            background_checker.testnet_dojos = testnet_dojos
            cache.invalidate()
    _save_submissions(submissions)
    return redirect(url_for('dojo_dashboard'))


# ── Admin routes (ADMIN_PAYNMS only) ─────────────────────────────────────────

def _cleanup_old_submissions():
    """Purge images and records for rejected/deleted submissions older than 3 days."""
    if not SUBMISSIONS_FILE.exists():
        return
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=3)
    try:
        submissions = _load_submissions()
    except Exception:
        return

    to_keep = []
    purged = 0
    for dojo in submissions:
        status = dojo.get('status')
        if status not in ('rejected', 'deleted'):
            to_keep.append(dojo)
            continue
        try:
            updated = datetime.fromisoformat(dojo.get('updated_at', ''))
        except (ValueError, TypeError):
            to_keep.append(dojo)
            continue
        if updated >= cutoff:
            to_keep.append(dojo)
            continue

        # ── Older than 3 days: delete files ───────────────────────────────────
        # Uploaded image (static/images/dojos/)
        if dojo.get('image_file'):
            p = DOJO_IMAGE_DIR / dojo['image_file']
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass

        # QR image (static/images/qr/)
        qr_filename = dojo.get('qr_filename')
        if not qr_filename:
            safe_name = ''.join(
                c if c.isalnum() or c in '-_' else '_'
                for c in dojo.get('name', 'dojo')
            )
            qr_filename = f"{safe_name}_{dojo.get('id', '')[:8]}.png"
        qr_path = Path(__file__).parent / 'static' / 'images' / 'qr' / qr_filename
        if qr_path.exists():
            try:
                qr_path.unlink()
            except OSError:
                pass

        purged += 1
        print(f"[CLEANUP] Purged {status} submission >3d: {dojo.get('name')} ({dojo.get('id', '')[:8]})")

    if purged:
        _save_submissions(to_keep)


def _require_admin():
    """Return paynym if admin, else None."""
    p = session.get('paynym')
    return p if p in ADMIN_PAYNMS else None


@app.route('/admin/dojos')
def admin_dojos():
    if not _require_admin():
        return redirect(url_for('index'))
    submissions = _load_submissions()
    # Resolve missing paynym aliases (one-time, lazy backfill)
    changed = False
    for d in submissions:
        if not d.get('paynym_alias') and d.get('paynym', '').startswith('PM8T'):
            alias = _resolve_paynym_alias(d['paynym'])
            if alias:
                d['paynym_alias'] = alias
                changed = True
    if changed:
        _save_submissions(submissions)
    pending  = [d for d in submissions if d.get('status') == 'pending']
    approved = [d for d in submissions if d.get('status') == 'approved']
    rejected = [d for d in submissions if d.get('status') == 'rejected']
    return render_template('admin_dojos.html',
                           pending=pending, approved=approved, rejected=rejected)


@app.route('/admin/dojos/<dojo_id>/approve', methods=['POST'])
def admin_approve(dojo_id):
    if not _require_admin():
        return redirect(url_for('index'))

    submissions = _load_submissions()
    dojo = next((d for d in submissions if d.get('id') == dojo_id), None)
    if not dojo:
        return redirect(url_for('admin_dojos'))

    # ── 1. Parse pairing_details JSON ─────────────────────────────────────────
    try:
        pairing_obj = json.loads(dojo.get('pairing_details', '{}'))
    except (json.JSONDecodeError, TypeError):
        pairing_obj = {}

    # ── 2. Resolve PayNym alias from payment code via paynym.rs ───────────────
    payment_code = dojo.get('paynym', '')
    paynym_alias = None
    paynym_url   = None
    if payment_code.startswith('PM8T'):
        try:
            import urllib.request, ssl
            req_data = json.dumps({"nym": payment_code}).encode()
            req = urllib.request.Request(
                'https://paynym.rs/api/v1/nym',
                data=req_data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                info = json.loads(resp.read())
            codes = info.get('codes', [])
            # prefer the code that matches the submitted payment_code
            matched = next((c for c in codes if c.get('code') == payment_code), None)
            nym_name = info.get('nymName') or info.get('nym_name')
            if nym_name:
                paynym_alias = f'+{nym_name}' if not nym_name.startswith('+') else nym_name
                paynym_url   = f'https://paynym.rs/{paynym_alias}'
        except Exception:
            pass  # proceed without alias

    # ── 3. Generate QR image from pairing JSON ────────────────────────────────
    qr_filename = None
    if pairing_obj:
        try:
            import qrcode as _qrcode
            safe_name = ''.join(c if c.isalnum() or c in '-_' else '_'
                                for c in dojo.get('name', 'dojo'))
            qr_filename = f"{safe_name}_{dojo_id[:8]}.png"
            qr_path = Path(__file__).parent / 'static' / 'images' / 'qr' / qr_filename
            qr_path.parent.mkdir(parents=True, exist_ok=True)
            qr_data = json.dumps(pairing_obj, separators=(',', ':'))
            qr = _qrcode.QRCode(
                error_correction=_qrcode.constants.ERROR_CORRECT_M,
                box_size=6, border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            from PIL import Image as _PILImage
            img = qr.make_image(fill_color='#000000', back_color='#ffffff')
            pil_img = img.get_image().convert('RGB')
            pil_img = pil_img.resize((400, 400), _PILImage.NEAREST)
            pil_img.save(str(qr_path))
        except Exception:
            qr_filename = None

    # ── 4. Build dojos_data.json entry ────────────────────────────────────────
    network  = dojo.get('network', 'mainnet')
    new_entry = {'name': dojo.get('name', '')}
    if paynym_alias:
        new_entry['paynym']     = paynym_alias
        new_entry['paynym_url'] = paynym_url
    if dojo.get('jurisdiction'):
        new_entry['jurisdiction'] = dojo['jurisdiction']
    if dojo.get('hardware'):
        new_entry['hardware'] = dojo['hardware']
    if qr_filename:
        new_entry['image'] = f'/static/images/qr/{qr_filename}'
    if pairing_obj:
        # pairing_details may be a wrapped {"pairing": {...}, "explorer": {...}}
        # or already a flat pairing object — handle both
        inner_pairing = pairing_obj.get('pairing', pairing_obj)
        inner_explorer = pairing_obj.get('explorer')
        if inner_pairing:
            new_entry['pairing'] = inner_pairing
        if inner_explorer:
            new_entry['explorer'] = inner_explorer
    if dojo.get('electrum_server'):
        new_entry['electrum_server'] = dojo['electrum_server']
    if dojo.get('nostr_x'):
        new_entry['nostr_x'] = dojo['nostr_x']
    # Store the raw pairing_details text (needed for signature verification)
    if dojo.get('pairing_details'):
        new_entry['pairing_details'] = dojo['pairing_details']
    # Store the BIP-137 pairing signature (use legacy signature_text as fallback)
    signature_content = dojo.get('pairing_signature') or dojo.get('signature_text', '')
    if signature_content:
        new_entry['signature'] = signature_content

    # Load, append, save dojos_data.json
    with open(DOJOS_DATA_FILE) as f:
        dojos_data = json.load(f)
    dojos_data.setdefault('mainnet', [])
    dojos_data.setdefault('testnet', [])
    dojos_data[network].append(new_entry)
    with open(DOJOS_DATA_FILE, 'w') as f:
        json.dump(dojos_data, f, indent=2, ensure_ascii=False)

    # ── 5. Mark submission approved and store qr filename ────────────────────
    dojo['status']      = 'approved'
    dojo['updated_at']  = datetime.now().isoformat()
    if qr_filename:
        dojo['qr_filename'] = qr_filename
    _save_submissions(submissions)

    # ── 6. Reload in-memory data so new node is checked immediately ───────────
    global mainnet_dojos, testnet_dojos
    mainnet_dojos, testnet_dojos = data_loader.load()
    background_checker.mainnet_dojos = mainnet_dojos
    background_checker.testnet_dojos = testnet_dojos
    cache.invalidate()

    return redirect(url_for('admin_dojos'))


@app.route('/admin/dojos/<dojo_id>/reject', methods=['POST'])
def admin_reject(dojo_id):
    if not _require_admin():
        return redirect(url_for('index'))
    submissions = _load_submissions()
    for d in submissions:
        if d.get('id') == dojo_id:
            d['status'] = 'rejected'
            d['updated_at'] = datetime.now().isoformat()
            break
    _save_submissions(submissions)
    return redirect(url_for('admin_dojos'))


@app.route('/admin/dojos/<dojo_id>/revoke', methods=['POST'])
def admin_revoke(dojo_id):
    """Revoke an approved dojo: remove from dojos_data.json and mark rejected."""
    if not _require_admin():
        return redirect(url_for('index'))

    submissions = _load_submissions()
    dojo = next((d for d in submissions if d.get('id') == dojo_id), None)
    if not dojo:
        return redirect(url_for('admin_dojos'))

    # Remove from dojos_data.json by matching name + network
    network = dojo.get('network', 'mainnet')
    name    = dojo.get('name', '')
    with open(DOJOS_DATA_FILE) as f:
        dojos_data = json.load(f)
    before = len(dojos_data.get(network, []))
    dojos_data[network] = [
        d for d in dojos_data.get(network, [])
        if d.get('name') != name
    ]
    if len(dojos_data[network]) < before:
        with open(DOJOS_DATA_FILE, 'w') as f:
            json.dump(dojos_data, f, indent=2, ensure_ascii=False)

    # Mark submission as rejected
    dojo['status']     = 'rejected'
    dojo['updated_at'] = datetime.now().isoformat()
    _save_submissions(submissions)

    # Reload in-memory data and invalidate cache
    global mainnet_dojos, testnet_dojos
    mainnet_dojos, testnet_dojos = data_loader.load()
    background_checker.mainnet_dojos = mainnet_dojos
    background_checker.testnet_dojos = testnet_dojos
    cache.invalidate()

    return redirect(url_for('admin_dojos'))


@app.route('/api/verify-pairing-signature', methods=['POST'])
def api_verify_pairing_signature():
    """Verify a BIP-137 signature of pairing details against the logged-in PayNym."""
    paynym = session.get('paynym')
    if not paynym:
        return jsonify({'valid': False, 'error': 'Not authenticated'}), 401
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    signature = data.get('signature', '').strip()
    if not message or not signature:
        return jsonify({'valid': False, 'error': 'Missing message or signature'}), 400
    try:
        valid = verify_pairing_signature(paynym, message, signature)
        return jsonify({'valid': valid})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500


@app.route('/api/verify-message', methods=['POST'])
def api_verify_message():
    """Public endpoint: verify a BIP-137 signature against a payment code or PayNym handle.

    Accepts JSON body:
      { "nym": "PM8T... or +handle", "message": "...", "signature": "..." }

    The ``nym`` field is resolved via paynym.rs, so either a full BIP47 payment
    code (PM8T…), a PayNym handle (+username), or a nymID are all accepted.

    If ``signature`` is an armored Bitcoin signed message block
    (-----BEGIN BITCOIN SIGNED MESSAGE-----) the message and compact signature
    are parsed from it automatically and the ``message`` field is ignored.
    """
    import urllib.request as _urlreq
    import ssl as _ssl

    data = request.get_json(silent=True) or {}
    nym_input = str(data.get('nym', '')).strip()
    message = str(data.get('message', '')).strip()
    signature = str(data.get('signature', '')).strip()

    if not nym_input or not signature:
        return jsonify({'valid': False, 'error': 'Missing nym or signature'}), 400

    # Resolve payment code via paynym.rs (accepts +handle, PM8T…, or nymID)
    try:
        req_data = json.dumps({'nym': nym_input}).encode()
        req = _urlreq.Request(
            'https://paynym.rs/api/v1/nym',
            data=req_data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        ctx = _ssl.create_default_context()
        with _urlreq.urlopen(req, timeout=10, context=ctx) as resp:
            info = json.loads(resp.read())
        codes = info.get('codes') or []
        payment_code = codes[0].get('code', '') if codes else ''
        if not payment_code:
            return jsonify({'valid': False, 'error': 'Could not resolve payment code from PayNym registry'}), 400
    except Exception:
        return jsonify({'valid': False, 'error': 'Could not reach PayNym registry'}), 503

    # Parse armored Bitcoin signed message format
    if signature.startswith('-----BEGIN BITCOIN SIGNED MESSAGE-----'):
        lines = signature.splitlines()
        try:
            sig_start = next(
                i for i, line in enumerate(lines)
                if line.strip() == '-----BEGIN SIGNATURE-----'
            )
            message = '\n'.join(lines[1:sig_start])
            after_header = [
                line for line in lines[sig_start + 1:]
                if not line.startswith('-----END')
            ]
            # Format: optional address line followed by base64 signature
            compact_sig = after_header[-1].strip() if after_header else ''
        except (StopIteration, IndexError):
            return jsonify({'valid': False, 'error': 'Could not parse armored signature format'}), 400
        signature = compact_sig

    if not message:
        return jsonify({'valid': False, 'error': 'Missing message'}), 400

    try:
        valid = verify_pairing_signature(payment_code, message, signature)
        return jsonify({'valid': valid, 'payment_code': payment_code})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """API endpoint to get current Dojo status."""
    try:
        cached = cache.get()
        if cached:
            return jsonify(cached)

        # Cache expired — serve stale data with a flag while background checker runs
        stale = cache.get_stale()
        if stale:
            return jsonify({**stale, "stale": True})

        # No data at all yet
        return jsonify({"loading": True, "message": "Updating node status..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    from datetime import datetime
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "nodes": {
            "mainnet": len(mainnet_dojos),
            "testnet": len(testnet_dojos)
        }
    })


@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static/images."""
    static_dir = os.path.join(app.root_path, 'static', 'images')
    return send_from_directory(
        static_dir,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == '__main__':
    print("Starting Dojobay web application...")
    print(f"Loaded {len(mainnet_dojos)} mainnet and {len(testnet_dojos)} testnet nodes")
    
    # Start background checker
    background_checker.start()
    
    print(f"Server starting on http://{HOST}:{PORT}")
    app.run(debug=DEBUG, host=HOST, port=PORT)
