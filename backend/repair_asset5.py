"""One-shot script to re-fingerprint Asset 5 (missing hashes)."""
import sys, cv2, os
sys.stdout.reconfigure(encoding="utf-8")

from app.db.models.user import User
from app.db.models.asset import Asset
from app.db.models.asset_frame import AssetFrame
from app.db.session import SessionLocal
from app.services.fingerprint.generator import get_phash, get_pdq, get_audio_fp

db = SessionLocal()
asset = db.query(Asset).filter(Asset.id == 5).first()
frames = db.query(AssetFrame).filter(AssetFrame.asset_id == 5).all()

print(f"Asset 5: {asset.asset_name}")
print(f"Frames to repair: {len(frames)}")

fixed = 0
for f in frames:
    if not os.path.exists(f.file_path):
        print(f"  SKIP frame {f.frame_number}: file missing")
        continue
    img = cv2.imread(f.file_path)
    if img is None:
        print(f"  SKIP frame {f.frame_number}: unreadable")
        continue
    f.phash_value = get_phash(img)
    f.pdq_hash = get_pdq(img)
    fixed += 1
    if fixed % 10 == 0:
        print(f"  ...processed {fixed} frames")

audio = get_audio_fp(asset.media_file_path)
if audio:
    asset.audio_fp = audio

db.commit()
print(f"\nDone! Re-fingerprinted {fixed}/{len(frames)} frames")
print(f"Audio fingerprint: {'YES' if audio else 'NO'}")

# Verify
check = db.query(AssetFrame).filter(AssetFrame.asset_id == 5).limit(3).all()
for c in check:
    print(f"  Frame {c.frame_number}: phash={c.phash_value is not None} pdq={c.pdq_hash is not None}")
db.close()
