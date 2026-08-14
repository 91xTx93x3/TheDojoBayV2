# QR Code Images - Local Assets

## Overview

This directory contains QR code images for all Dojo nodes (mainnet and testnet). These images were downloaded from dojobay.pw and are now served locally to ensure reliability and faster loading times.

## Directory Structure

```
static/images/qr/
├── Compiler_compiler.png
├── otto_OO4.png
├── @maxtannahill_New.png
├── jordan_HIrIlPX5.png
├── Razzle_Dazzle_Razzle-Dazzle.png
├── Syndicate_Systems_Syndicate-Systems.png
├── Btcwrestle_Btcwrestle.png
├── BottomshelfBTC_BottomshelfBTC.png
├── xTx_Yellow_xTx-Yellow.png
├── xTx_Red_xTx-Red.png
├── xTx_Tanto_I_Tanto-I--xTx--1.png
├── xTx_Tanto_E_Tanto-E--xTx-.png
├── Expatriotic_expatriotic.png
├── arthur_(Out_Of_Service)_E3029.png
├── @Libertarian_libtest.png
├── wanderinKing072_image-1.png
├── xTx_Blue_xtx-Blue-Dojobay.png
└── BottomshelfBTC_bottomshelfbtc-1.png
```

## File Naming Convention

Files are named using the pattern: `{NodeName}_{OriginalFileName}.png`

- Node names are sanitized (spaces replaced with underscores, special characters removed)
- Original filenames are preserved for reference
- Example: `Compiler_compiler.png` for the Compiler node

## Maintenance Scripts

### Download QR Images

```bash
./venv/bin/python scripts/download_qr_images.py
```

This script:

- Reads node definitions from `app.py`
- Downloads all QR images from external URLs
- Saves them to `static/images/qr/` with proper naming
- Reports download success/failure

### Update Image Paths

```bash
./venv/bin/python scripts/update_image_paths.py
```

This script:

- Updates all image URLs in `app.py` to use local paths
- Converts external URLs to `/static/images/qr/{filename}`
- Reports number of paths updated

## Usage in Templates

Images are referenced in `templates/index.html`:

```javascript
${dojo.image ? `<img src="${dojo.image}" alt="${dojo.name} QR" class="dojo-qr img-fluid">` : ''}
```

The `dojo.image` property contains the local path (e.g., `/static/images/qr/Compiler_compiler.png`).

## Styling

QR images use the `.dojo-qr` CSS class defined in `templates/index.html`:

```css
.dojo-qr {
  max-width: 200px;
  max-height: 200px;
  border: 3px solid var(--primary); /* Red border */
  border-radius: 8px;
  margin: 1rem 0;
  padding: 10px;
  background-color: #ffffff; /* White background for visibility */
  box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
}
```

## Adding New Nodes

When adding a new node with a QR code:

1. Add the node definition to `MAINNET_DOJOS` or `TESTNET_DOJOS` in `app.py`
2. Include the external image URL in the `"image"` field
3. Run `scripts/download_qr_images.py` to download the new image
4. Run `scripts/update_image_paths.py` to update the path to local
5. Restart the Flask server

## Image Count

- **Mainnet nodes**: 14 images
- **Testnet nodes**: 5 images
- **Total**: 19 images

## Notes

- All images are PNG format
- Average file size: ~13KB per image
- Images are served statically by Flask
- No external dependencies for image loading
- Faster page load times compared to external URLs
