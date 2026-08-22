
#!/bin/bash

echo "========================================="
echo "   Installation de Relevé VE"
echo "========================================="

# 1. Vérification de la présence du script Python
if [ ! -f "charge_electrique-v8.1.py" ]; then
    echo "❌ Erreur : Le fichier 'charge_voiture_electrique.py' est introuvable."
    echo "Veuillez lancer ce script d'installation depuis le dossier contenant charge_electrique.py."
    exit 1
fi

# 2. Installation des dépendances système
echo -e "\n📦 Installation des dépendances (Tkinter et FPDF)..."
echo "Votre mot de passe administrateur va être demandé."
sudo apt update
sudo apt install -y python3-tk python3-fpdf

# 3. Création du dossier d'installation caché dans le répertoire utilisateur
INSTALL_DIR="$HOME/.local/share/ReleveVE"
echo -e "\n📁 Création du répertoire $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# 4. Copie du script Python et attribution des droits d'exécution
echo "⚙️ Copie du script..."
cp charge_electrique-v8.1.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/charge_electrique-v8.1.py"

# 5. Création du fichier .desktop pour le menu Linux Mint
DESKTOP_FILE="$HOME/.local/share/applications/charge_electrique.desktop"
echo "📝 Création du raccourci dans le menu ($DESKTOP_FILE)..."

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Relevés VE
Comment=Suivi de consommation de la voiture électrique
Exec=python3 $INSTALL_DIR/charge_electrique-v8.1.py
Icon=utilities-system-monitor
Terminal=false
Type=Application
Categories=Utility;Finance;
EOF

# 6. Rafraîchissement des menus (Cinnamon / Mate / XFCE)
update-desktop-database "$HOME/.local/share/applications/" 2>/dev/null

echo -e "\n✅ Installation terminée avec succès !"
echo "Vous pouvez maintenant trouver 'Relevés VE' dans le menu des applications de Linux Mint."