#!/bin/bash

echo "==============================================="
echo " Installation de Suivi de Charge VE (v8.5)"
echo "==============================================="

# Vérification du fichier Python
SCRIPT_SOURCE="charge_electrique-v8.5.py"
if [ ! -f "$SCRIPT_SOURCE" ]; then
    echo "❌ Erreur : Le fichier '$SCRIPT_SOURCE' est introuvable."
    echo "Assurez-vous que ce script d'installation est dans le même dossier que le fichier Python."
    exit 1
fi

# 1. Dépendances système (Demande le mot de passe sudo)
echo -e "\n[1/4] Installation des paquets système requis..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-tk python3-pil.imagetk

# 2. Préparation des répertoires de l'application
APP_DIR="$HOME/.local/share/ReleveVE"
echo -e "\n[2/4] Création de l'arborescence dans $APP_DIR..."
mkdir -p "$APP_DIR/bin"
mkdir -p "$HOME/.local/share/applications"

# 3. Environnement virtuel et dépendances Python
echo -e "\n[3/4] Configuration de l'environnement virtuel Python isolé..."
python3 -m venv "$APP_DIR/venv"

# Installation des paquets PIP dans le venv
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install fpdf Pillow

# Copie du script principal à son emplacement définitif
cp "$SCRIPT_SOURCE" "$APP_DIR/bin/charge_electrique-v8.5.py"
chmod +x "$APP_DIR/bin/charge_electrique-v8.5.py"

# 4. Création du raccourci dans le menu des applications
echo -e "\n[4/4] Création du raccourci dans le menu système..."
DESKTOP_FILE="$HOME/.local/share/applications/suivi-charge-ve.desktop"

cat > "$DESKTOP_FILE" << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=Suivi Charge VE
Comment=Gestion de la consommation de la voiture électrique
Exec=$APP_DIR/venv/bin/python $APP_DIR/bin/charge_electrique-v8.5.py
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;Finance;
EOL

chmod +x "$DESKTOP_FILE"

echo -e "\n==============================================="
echo " ✅ Installation terminée avec succès !"
echo " Vous pouvez maintenant lancer 'Suivi Charge VE' directement depuis le menu de votre bureau."
echo "==============================================="