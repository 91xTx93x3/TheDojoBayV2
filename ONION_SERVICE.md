# Dojobay Hidden Service (Onion Address)

## 🧅 Onion Address
```
dojobayswp3qv5iwamualgzlv6faenb5me677wcs3detwmjcfv3ja7ad.onion
```

## 📋 Configuración

### Tor Hidden Service
- **Directorio:** `/var/lib/tor/hidden_service_dojobay/`
- **Puerto:** 80 → 127.0.0.1:80
- **Tipo:** v3 onion address (ed25519)
- **Vanity:** Empieza con "dojobay"

### Nginx
- **Configuración:** `/etc/nginx/sites-available/dojobay-onion`
- **Escucha:** 127.0.0.1:80
- **Proxy:** → Flask (127.0.0.1:5002)

### Archivos del Hidden Service
```
/var/lib/tor/hidden_service_dojobay/
├── hostname                    (dirección .onion)
├── hs_ed25519_public_key      (clave pública)
└── hs_ed25519_secret_key      (clave privada - CRÍTICO)
```

## 🔧 Comandos Útiles

### Verificar estado de Tor
```bash
sudo systemctl status tor@default
```

### Ver logs de Tor
```bash
sudo journalctl -u tor@default -f
```

### Reiniciar servicios
```bash
sudo systemctl restart tor@default
sudo systemctl reload nginx
```

### Probar acceso local
```bash
curl -H "Host: dojobayswp3qv5iwamualgzlv6faenb5me677wcs3detwmjcfv3ja7ad.onion" http://127.0.0.1:80/
```

### Probar acceso por Tor
```bash
curl --socks5-hostname 127.0.0.1:9050 http://dojobayswp3qv5iwamualgzlv6faenb5me677wcs3detwmjcfv3ja7ad.onion/
```

## 🔐 Seguridad

**⚠️ IMPORTANTE:**
- Las claves privadas están en `/var/lib/tor/hidden_service_dojobay/hs_ed25519_secret_key`
- Hacer backup regular de todo el directorio
- Permisos: `700` para el directorio, `600` para los archivos
- Owner: `debian-tor:debian-tor`

## 📦 Backup

El backup completo está en: `/root/dojobay_backup_20251126_183334/`

Para restaurar:
```bash
bash /root/dojobay_backup_20251126_183334/RESTORE.sh
```

## �� Acceso

### Clearnet (HTTPS)
https://dojobay.pw

### Tor (HTTP)
http://dojobayswp3qv5iwamualgzlv6faenb5me677wcs3detwmjcfv3ja7ad.onion
