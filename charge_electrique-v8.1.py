import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import datetime
import json
import shutil
from collections import defaultdict
from fpdf import FPDF

# --- Informations sur l'application ---
APP_NAME = "Suivi de Charge - Voiture Électrique"
APP_VERSION = "v8.1"
APP_DATE = "Août 2026"
APP_AUTHOR = "Durand Joël"
APP_EMAIL = "rd66lago@gmail.com"

# --- Fichiers ---
DB_FILE = os.path.expanduser("~/.local/share/ReleveVE/.releve_ve_data.db")
CONFIG_FILE = os.path.expanduser("~/.local/share/ReleveVE/.releve_ve_config.json")

# --- Thème Light "Pure Flat" Adouci (Anti-fatigue visuelle) ---
BG_COLOR = "#e6ece8"       # Gris-vert pastel très doux pour le fond
SURFACE_COLOR = "#f0f4f1"  # Blanc cassé sauge
ACCENT_COLOR = "#9cbfa3"   # Vert sauge doux
ACCENT_HOVER = "#83a88a"   # Vert sauge un peu plus soutenu
TEXT_COLOR = "#2d3830"     # Anthracite teinté de vert
TEXT_MUTED = "#7a8c80"     # Gris-vert moyen
DANGER_COLOR = "#e57373"
WARNING_COLOR = "#f6a855"

class ReleveVEApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} - {APP_VERSION}")
        self.root.geometry("1200x950")
        self.root.configure(bg=BG_COLOR)

        self.donnees = []
        self.id_edition = None
        self.prix_kwh_defaut = ""
        self.filtre_mois_courant = "Tous les mois"

        self.sauvegarde_automatique()
        self.charger_config()
        self.initialiser_bdd()
        
        self.creer_menu()
        self.creer_interface()
        self.charger_donnees()
        
        self.root.update()
        self.dessiner_graphiques()
        
        self.root.after(100, lambda: self.afficher_a_propos(startup=True))

    def sauvegarde_automatique(self):
        if os.path.exists(DB_FILE):
            backup_dir = os.path.expanduser("~/.local/share/ReleveVE/Sauvegardes_VE")
            os.makedirs(backup_dir, exist_ok=True)
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            fichier_backup = os.path.join(backup_dir, f"releve_ve_backup_{date_str}.db")
            
            try:
                if not os.path.exists(fichier_backup):
                    shutil.copy2(DB_FILE, fichier_backup)
            except Exception as e:
                print(f"Erreur de sauvegarde : {e}")

    def charger_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.prix_kwh_defaut = str(config.get("prix_kwh", ""))
            except:
                pass

    def sauvegarder_config(self, prix):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"prix_kwh": prix}, f, indent=4)
        except:
            pass

    def initialiser_bdd(self):
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS releves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                charge REAL,
                prix_kwh REAL,
                km REAL
            )
        ''')
        
        cursor.execute("PRAGMA table_info(releves)")
        colonnes_existantes = [col[1] for col in cursor.fetchall()]
        
        if "debut_charge" not in colonnes_existantes:
            cursor.execute("ALTER TABLE releves ADD COLUMN debut_charge REAL DEFAULT 0")
        if "fin_charge" not in colonnes_existantes:
            cursor.execute("ALTER TABLE releves ADD COLUMN fin_charge REAL DEFAULT 0")

        conn.commit()
        conn.close()

    def creer_menu(self):
        menubar = tk.Menu(self.root, bg=SURFACE_COLOR, fg=TEXT_COLOR, bd=0, relief=tk.FLAT)
        
        menu_fichier = tk.Menu(menubar, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR, bd=0, relief=tk.FLAT)
        menu_fichier.add_command(label="Éditer Modèle Vierge PDF", command=self.generer_modele_vierge)
        menu_fichier.add_command(label="Exporter la vue actuelle en PDF", command=self.exporter_pdf)
        menu_fichier.add_separator()
        menu_fichier.add_command(label="Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=menu_fichier)
        
        menu_aide = tk.Menu(menubar, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR, bd=0, relief=tk.FLAT)
        menu_aide.add_command(label="À propos de l'application...", command=lambda: self.afficher_a_propos(startup=False))
        menubar.add_cascade(label="?", menu=menu_aide)

        self.root.config(menu=menubar)

    def afficher_a_propos(self, startup=False):
        win_propos = tk.Toplevel(self.root)
        win_propos.title("À propos")
        win_propos.geometry("520x440")
        win_propos.configure(bg=SURFACE_COLOR)
        win_propos.overrideredirect(True) 
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 260
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 220
        win_propos.geometry(f"+{x}+{y}")
        
        win_propos.transient(self.root)
        win_propos.grab_set()

        frame_head = tk.Frame(win_propos, bg=ACCENT_COLOR, pady=15)
        frame_head.pack(fill=tk.X)
        
        tk.Label(frame_head, text=APP_NAME, bg=ACCENT_COLOR, fg=TEXT_COLOR, font=("Arial", 14, "bold")).pack()
        tk.Label(frame_head, text=f"Version : {APP_VERSION}  -  {APP_DATE}", bg=ACCENT_COLOR, fg=TEXT_COLOR, font=("Arial", 10)).pack(pady=(5, 0))

        frame_desc = tk.Frame(win_propos, bg=SURFACE_COLOR, padx=20, pady=15)
        frame_desc.pack(fill=tk.BOTH, expand=True)

        explication = (
            "Cette application permet d'enregistrer et d'analyser vos recharges "
            "de véhicule électrique en toute simplicité :\n\n"
            "  • Saisie du taux de charge initial et final (en %)\n"
            #"  • Calcul automatique du coût et de la consommation (kWh/100km)\n" a refaire
            "  • Filtrage des relevés par mois avec statistiques adaptées\n"
            "  • Graphiques interactifs détaillés\n"
            "  • Exportation PDF automatique de la période sélectionnée\n"
            "  • Sauvegarde locale sécurisée dans votre répertoire personnel\n\n"
        )
        tk.Label(frame_desc, text=explication, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Arial", 10), justify=tk.LEFT, wraplength=460).pack(anchor="w")

        btn_ok = tk.Button(frame_desc, text="OK, Accéder à l'application", bg=ACCENT_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, font=("Arial", 10, "bold"), command=win_propos.destroy, padx=20, pady=5)
        btn_ok.pack(pady=20)

        frame_foot = tk.Frame(win_propos, bg=BG_COLOR, pady=10)
        frame_foot.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(frame_foot, text=f"© {datetime.date.today().year} - {APP_AUTHOR} - Tous droits réservés.", bg=BG_COLOR, fg=TEXT_MUTED, font=("Arial", 9, "bold")).pack()
        tk.Label(frame_foot, text=f"Contact / Assistance : {APP_EMAIL}", bg=BG_COLOR, fg=TEXT_MUTED, font=("Arial", 9)).pack(pady=(3, 0))
        
        if startup:
            self.root.wait_window(win_propos)

    def creer_interface(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Treeview", background=SURFACE_COLOR, foreground=TEXT_COLOR, fieldbackground=SURFACE_COLOR, borderwidth=0)
        style.map('Treeview', background=[('selected', ACCENT_HOVER)], foreground=[('selected', SURFACE_COLOR)])
        style.configure("Treeview.Heading", background=BG_COLOR, foreground=TEXT_COLOR, font=("Arial", 10, "bold"), borderwidth=0, relief=tk.FLAT)

        # --- 1. Zone des 2 Graphiques (En haut) ---
        frame_graphiques = tk.Frame(self.root, bg=BG_COLOR)
        frame_graphiques.pack(fill=tk.BOTH, padx=10, pady=5)

        frame_gauche = tk.Frame(frame_graphiques, bg=SURFACE_COLOR)
        frame_gauche.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        frame_titre_g = tk.Frame(frame_gauche, bg=SURFACE_COLOR)
        frame_titre_g.pack(fill=tk.X, pady=(5, 2))
        tk.Label(frame_titre_g, text="Charges du mois :", bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(10, 5))
        
        self.combo_mois_gauche = ttk.Combobox(frame_titre_g, state="readonly", width=10)
        self.combo_mois_gauche.pack(side=tk.LEFT)
        self.combo_mois_gauche.bind("<<ComboboxSelected>>", lambda e: self.dessiner_graphiques())
        
        self.canvas_gauche = tk.Canvas(frame_gauche, bg=SURFACE_COLOR, height=190, bd=0, highlightthickness=0)
        self.canvas_gauche.pack(fill=tk.BOTH, expand=True)
        
        self.lbl_total_gauche = tk.Label(frame_gauche, text="Total Charge : -- kWh | Prix : -- €", bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold"))
        self.lbl_total_gauche.pack(pady=(2, 5))

        frame_droite = tk.Frame(frame_graphiques, bg=SURFACE_COLOR)
        frame_droite.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(frame_droite, text="Évolution de la conso. mois par mois (kWh/100km)", bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")).pack(pady=(5, 2))
        
        self.canvas_droite = tk.Canvas(frame_droite, bg=SURFACE_COLOR, height=190, bd=0, highlightthickness=0)
        self.canvas_droite.pack(fill=tk.BOTH, expand=True)
        
        self.lbl_total_droite = tk.Label(frame_droite, text="Total Charge : -- kWh | Prix : -- €", bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold"))
        self.lbl_total_droite.pack(pady=(2, 5))
        
        self.canvas_gauche.bind("<Configure>", lambda e: self.dessiner_graphiques())
        self.canvas_droite.bind("<Configure>", lambda e: self.dessiner_graphiques())

        # --- 2. Ligne de Saisie (Sous les graphiques) ---
        frame_saisie = tk.Frame(self.root, bg=SURFACE_COLOR, bd=0, highlightthickness=0)
        frame_saisie.pack(fill=tk.X, padx=10, pady=10)

        entry_kwargs = {
            "bg": BG_COLOR, 
            "fg": TEXT_COLOR, 
            "insertbackground": TEXT_COLOR, 
            "relief": tk.FLAT, 
            "bd": 0, 
            "highlightthickness": 0
        }

        tk.Label(frame_saisie, text="Date :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, padx=3, pady=12, sticky="e")
        self.ent_date = tk.Entry(frame_saisie, width=10, **entry_kwargs)
        self.ent_date.grid(row=0, column=1, padx=3, pady=12)
        self.ent_date.insert(0, datetime.date.today().strftime("%d/%m/%Y"))

        tk.Label(frame_saisie, text="Début (%) :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=2, padx=3, pady=12, sticky="e")
        self.ent_debut = tk.Entry(frame_saisie, width=6, **entry_kwargs)
        self.ent_debut.grid(row=0, column=3, padx=3, pady=12)

        tk.Label(frame_saisie, text="Fin (%) :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=4, padx=3, pady=12, sticky="e")
        self.ent_fin = tk.Entry(frame_saisie, width=6, **entry_kwargs)
        self.ent_fin.grid(row=0, column=5, padx=3, pady=12)

        tk.Label(frame_saisie, text="Charge (kWh) :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=6, padx=3, pady=12, sticky="e")
        self.ent_charge = tk.Entry(frame_saisie, width=8, **entry_kwargs)
        self.ent_charge.grid(row=0, column=7, padx=3, pady=12)

        tk.Label(frame_saisie, text="Km total :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=8, padx=3, pady=12, sticky="e")
        self.ent_km = tk.Entry(frame_saisie, width=10, **entry_kwargs)
        self.ent_km.grid(row=0, column=9, padx=3, pady=12)

        tk.Label(frame_saisie, text="Prix kWh (€) :", bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=10, padx=3, pady=12, sticky="e")
        self.ent_prix_kwh = tk.Entry(frame_saisie, width=8, **entry_kwargs)
        self.ent_prix_kwh.grid(row=0, column=11, padx=3, pady=12)
        if self.prix_kwh_defaut:
            self.ent_prix_kwh.insert(0, self.prix_kwh_defaut)

        self.btn_ajouter = tk.Button(frame_saisie, text="Ajouter", bg=ACCENT_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, highlightthickness=0, font=("Arial", 10, "bold"), command=self.valider_saisie)
        self.btn_ajouter.grid(row=0, column=12, padx=(10, 3), pady=12)

        self.btn_annuler = tk.Button(frame_saisie, text="X", bg=DANGER_COLOR, fg="white", relief=tk.FLAT, bd=0, highlightthickness=0, font=("Arial", 10, "bold"), command=self.reinitialiser_formulaire)
        self.btn_annuler.grid(row=0, column=13, padx=(2, 10), pady=12)
        self.btn_annuler.grid_remove()

        # --- 3. Barre de filtrage et Tableau (En bas) ---
        frame_filtre = tk.Frame(self.root, bg=BG_COLOR)
        frame_filtre.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(frame_filtre, text="🔍 Filtrer le tableau & l'export PDF :", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 5))
        
        self.combo_mois = ttk.Combobox(frame_filtre, state="readonly", width=15)
        self.combo_mois.pack(side=tk.LEFT, padx=5)
        self.combo_mois.bind("<<ComboboxSelected>>", self.sur_changement_filtre)

        btn_reset_filtre = tk.Button(frame_filtre, text="Voir tout", bg=ACCENT_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, font=("Arial", 9, "bold"), command=self.reset_filtre_mois)
        btn_reset_filtre.pack(side=tk.LEFT, padx=5)

        colonnes = ("date", "debut_charge", "fin_charge", "charge", "prix_kwh", "km", "conso_moyenne", "cout_total")
        self.tree = ttk.Treeview(self.root, columns=colonnes, show="headings", height=10)
        self.tree.heading("date", text="Date")
        self.tree.heading("debut_charge", text="Début (%)")
        self.tree.heading("fin_charge", text="Fin (%)")
        self.tree.heading("charge", text="Charge (kWh)")
        self.tree.heading("prix_kwh", text="Prix kWh (€)")
        self.tree.heading("km", text="Kilométrage")
        self.tree.heading("conso_moyenne", text="Conso (kWh/100km)")
        self.tree.heading("cout_total", text="Coût Total (€)")
        
        self.tree.column("date", width=85, anchor="center")
        self.tree.column("debut_charge", width=75, anchor="center")
        self.tree.column("fin_charge", width=75, anchor="center")
        self.tree.column("charge", width=90, anchor="center")
        self.tree.column("prix_kwh", width=85, anchor="center")
        self.tree.column("km", width=95, anchor="center")
        self.tree.column("conso_moyenne", width=130, anchor="center")
        self.tree.column("cout_total", width=95, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<<TreeviewSelect>>", self.sur_selection_ligne)
        self.tree.bind("<Button-3>", self.sur_clic_droit)
        self.tree.bind("<Delete>", lambda e: self.supprimer_releve())

        self.menu_contextuel = tk.Menu(self.root, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR, relief=tk.FLAT)
        self.menu_contextuel.add_command(label="✏️ Modifier ce relevé", command=self.preparer_modification)
        self.menu_contextuel.add_command(label="🗑️ Supprimer ce relevé", command=self.supprimer_releve)

        self.actualiser_liste_mois()
        self.afficher_donnees()

    def sur_selection_ligne(self, event):
        selection = self.tree.selection()
        if selection:
            self.preparer_modification()

    def sur_clic_droit(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu_contextuel.post(event.x_root, event.y_root)

    def sur_changement_filtre(self, event):
        self.filtre_mois_courant = self.combo_mois.get()
        self.afficher_donnees()

    def reset_filtre_mois(self):
        self.filtre_mois_courant = "Tous les mois"
        self.combo_mois.set("Tous les mois")
        self.afficher_donnees()

    def actualiser_liste_mois(self):
        if not hasattr(self, "combo_mois"):
            return
            
        mois_presents = set()
        for d in self.donnees:
            try:
                mois_presents.add(d["date"][3:])
            except Exception:
                pass
        
        liste_mois = sorted(list(mois_presents), key=lambda x: (x[-4:], x[:2]))
        
        liste_filtre = ["Tous les mois"] + liste_mois
        self.combo_mois["values"] = liste_filtre
        if self.filtre_mois_courant not in liste_filtre:
            self.filtre_mois_courant = "Tous les mois"
        self.combo_mois.set(self.filtre_mois_courant)
        
        self.combo_mois_gauche["values"] = liste_mois
        if liste_mois:
            if not self.combo_mois_gauche.get() in liste_mois:
                self.combo_mois_gauche.set(liste_mois[-1])
        else:
            self.combo_mois_gauche.set("")

    def reinitialiser_formulaire(self):
        self.id_edition = None
        self.btn_ajouter.config(text="Ajouter", bg=ACCENT_COLOR, fg=TEXT_COLOR)
        self.btn_annuler.grid_remove()
        
        self.ent_date.delete(0, tk.END)
        self.ent_date.insert(0, datetime.date.today().strftime("%d/%m/%Y"))
        self.ent_debut.delete(0, tk.END)
        self.ent_debut.insert(0, "")
        self.ent_fin.delete(0, tk.END)
        self.ent_fin.insert(0, "")
        self.ent_charge.delete(0, tk.END)
        self.ent_charge.insert(0, "")
        self.ent_km.delete(0, tk.END)
        self.ent_km.insert(0, "")
        
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection()[0])

    def charger_donnees(self):
        self.donnees = []
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, debut_charge, fin_charge, charge, prix_kwh, km FROM releves ORDER BY km ASC")
        lignes = cursor.fetchall()
        conn.close()

        for ligne in lignes:
            self.donnees.append({
                "id": ligne[0],
                "date": ligne[1],
                "debut_charge": ligne[2],
                "fin_charge": ligne[3],
                "charge": ligne[4],
                "prix_kwh": ligne[5],
                "km": ligne[6]
            })
        self.recalculer_donnees()
        self.actualiser_liste_mois()

    def valider_saisie(self):
        date_val = self.ent_date.get()
        debut = self.ent_debut.get().replace(',', '.')
        fin = self.ent_fin.get().replace(',', '.')
        charge = self.ent_charge.get().replace(',', '.')
        prix_kwh = self.ent_prix_kwh.get().replace(',', '.')
        km = self.ent_km.get().replace(',', '.')

        if date_val and debut and fin and charge and prix_kwh and km:
            try:
                debut_f = float(debut)
                fin_f = float(fin)
                charge_f = float(charge)
                prix_kwh_f = float(prix_kwh)
                km_f = float(km)
                
                if str(prix_kwh_f) != self.prix_kwh_defaut:
                    self.sauvegarder_config(prix_kwh_f)
                    self.prix_kwh_defaut = str(prix_kwh_f)
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                if self.id_edition is not None:
                    cursor.execute('''UPDATE releves 
                                      SET date=?, debut_charge=?, fin_charge=?, charge=?, prix_kwh=?, km=? 
                                      WHERE id=?''', 
                                   (date_val, debut_f, fin_f, charge_f, prix_kwh_f, km_f, self.id_edition))
                else:
                    cursor.execute('''INSERT INTO releves 
                                      (date, debut_charge, fin_charge, charge, prix_kwh, km) 
                                      VALUES (?, ?, ?, ?, ?, ?)''', 
                                   (date_val, debut_f, fin_f, charge_f, prix_kwh_f, km_f))
                
                conn.commit()
                conn.close()

                self.reinitialiser_formulaire()
                self.charger_donnees()
                self.afficher_donnees()
                
            except ValueError:
                messagebox.showwarning("Erreur", "Veuillez entrer des nombres valides.")
        else:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs.")

    def preparer_modification(self):
        selection = self.tree.selection()
        if not selection: return
        self.id_edition = int(selection[0])
        valeurs = self.tree.item(selection[0], "values")
        
        self.ent_date.delete(0, tk.END)
        self.ent_date.insert(0, valeurs[0])
        self.ent_debut.delete(0, tk.END)
        self.ent_debut.insert(0, valeurs[1].replace('%', ''))
        self.ent_fin.delete(0, tk.END)
        self.ent_fin.insert(0, valeurs[2].replace('%', ''))
        self.ent_charge.delete(0, tk.END)
        self.ent_charge.insert(0, valeurs[3])
        self.ent_prix_kwh.delete(0, tk.END)
        self.ent_prix_kwh.insert(0, valeurs[4])
        self.ent_km.delete(0, tk.END)
        self.ent_km.insert(0, valeurs[5]) 
        
        self.btn_ajouter.config(text="Valider modif.", bg=WARNING_COLOR, fg=SURFACE_COLOR)
        self.btn_annuler.grid()

    def supprimer_releve(self):
        selection = self.tree.selection()
        if not selection: return
            
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce relevé ?"):
            id_db = int(selection[0])
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM releves WHERE id=?", (id_db,))
            conn.commit()
            conn.close()
            
            self.reinitialiser_formulaire()
            self.charger_donnees()
            self.afficher_donnees()

    def recalculer_donnees(self):
        for i in range(len(self.donnees)):
            charge = float(self.donnees[i]["charge"])
            prix_kwh = float(self.donnees[i]["prix_kwh"])
            cout_total = round(charge * prix_kwh, 2)
            self.donnees[i]["cout_total"] = cout_total
            
            if i == 0:
                self.donnees[i]["conso_100km"] = "N/A"
            else:
                km_actuel = float(self.donnees[i]["km"])
                km_prec = float(self.donnees[i-1]["km"])
                distance = km_actuel - km_prec
                if distance > 0:
                    self.donnees[i]["conso_100km"] = round((charge / distance) * 100, 2)
                else:
                    self.donnees[i]["conso_100km"] = "N/A"

    def afficher_donnees(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for d in self.donnees:
            if self.filtre_mois_courant == "Tous les mois" or d["date"].endswith(self.filtre_mois_courant):
                self.tree.insert("", tk.END, iid=str(d["id"]), values=(
                    d["date"], 
                    f"{d.get('debut_charge', 0):g}%", 
                    f"{d.get('fin_charge', 0):g}%", 
                    d["charge"], 
                    d["prix_kwh"], 
                    d["km"], 
                    d.get("conso_100km", ""),
                    d.get("cout_total", "")
                ))
        
        self.dessiner_graphiques()

    def _calculer_consommation_par_mois(self):
        par_mois = defaultdict(list)
        for d in self.donnees:
            val_conso = d.get("conso_100km", "N/A")
            if val_conso != "N/A":
                try:
                    mois_annee = d["date"][3:]
                    par_mois[mois_annee].append(float(val_conso))
                except Exception:
                    pass
        
        res = {}
        for k, vals in par_mois.items():
            res[k] = round(sum(vals) / len(vals), 2)
        return res

    def dessiner_graphiques(self):
        self._dessiner_graphique_gauche()
        self._dessiner_graphique_droite()

    def _dessiner_graphique_gauche(self):
        self.canvas_gauche.delete("all")
        mois_choisi = self.combo_mois_gauche.get()
        
        if not mois_choisi:
            self.canvas_gauche.create_text(250, 90, text="Sélectionnez un mois pour voir les jours", fill=TEXT_MUTED, font=("Arial", 11, "italic"))
            self.lbl_total_gauche.config(text="Total Charge : -- kWh  |  Total Prix : -- €")
            return

        data_jours = defaultdict(float)
        total_charge = 0.0
        total_prix = 0.0
        
        for d in self.donnees:
            if d["date"].endswith(mois_choisi):
                jour = d["date"][:2]
                charge = float(d.get("charge", 0))
                prix = float(d.get("cout_total", 0))
                data_jours[jour] += charge
                total_charge += charge
                total_prix += prix
                
        self.lbl_total_gauche.config(text=f"Total Charge : {total_charge:.2f} kWh  |  Total Prix : {total_prix:.2f} €")
        
        if not data_jours:
            self.canvas_gauche.create_text(250, 90, text="Aucune donnée pour ce mois", fill=TEXT_MUTED, font=("Arial", 11, "italic"))
            return

        largeur, hauteur = self.canvas_gauche.winfo_width(), self.canvas_gauche.winfo_height()
        if largeur <= 1: largeur = 500
        if hauteur <= 1: hauteur = 190

        marge_x, marge_y = 30, 30
        zone_l, zone_h = largeur - 2 * marge_x, hauteur - 2 * marge_y

        self.canvas_gauche.create_line(marge_x, hauteur - marge_y, largeur - marge_x + 10, hauteur - marge_y, fill=TEXT_MUTED, width=2)
        
        jours = sorted(list(data_jours.keys()))
        val_max = max(data_jours.values()) if max(data_jours.values()) > 0 else 1
        plafond = val_max * 1.25
        
        pas_x = zone_l / len(jours) if len(jours) > 0 else zone_l
        largeur_barre = min(pas_x * 0.6, 40)
        
        for i, jour in enumerate(jours):
            val = data_jours[jour]
            x_centre = marge_x + i * pas_x + pas_x / 2
            
            h_barre = (val / plafond) * zone_h
            x0 = x_centre - largeur_barre / 2
            y0 = hauteur - marge_y - h_barre
            x1 = x_centre + largeur_barre / 2
            y1 = hauteur - marge_y
            
            self.canvas_gauche.create_rectangle(x0, y0, x1, y1, fill=ACCENT_COLOR, outline=ACCENT_COLOR)
            self.canvas_gauche.create_text(x_centre, y0 - 10, text=f"{val:g}", font=("Arial", 8, "bold"), fill=TEXT_COLOR)
            self.canvas_gauche.create_text(x_centre, hauteur - marge_y + 12, text=jour, font=("Arial", 8), fill=TEXT_MUTED)

    def _dessiner_graphique_droite(self):
        self.canvas_droite.delete("all")
        
        total_charge_global = sum(float(d.get("charge", 0)) for d in self.donnees)
        total_prix_global = sum(float(d.get("cout_total", 0)) for d in self.donnees)
        self.lbl_total_droite.config(text=f"Total Charge : {total_charge_global:.2f} kWh  |  Total Prix : {total_prix_global:.2f} €")
        
        data_mois = self._calculer_consommation_par_mois()
        cles_mois = list(data_mois.keys())

        if len(cles_mois) < 1:
            self.canvas_droite.create_text(250, 90, text="Ajoutez des relevés pour voir la courbe", fill=TEXT_MUTED, font=("Arial", 11, "italic"))
            return

        largeur, hauteur = self.canvas_droite.winfo_width(), self.canvas_droite.winfo_height()
        if largeur <= 1: largeur = 500
        if hauteur <= 1: hauteur = 190

        marge_x, marge_y = 40, 30
        zone_dessin_l, zone_dessin_h = largeur - 2 * marge_x, hauteur - 2 * marge_y

        self.canvas_droite.create_line(marge_x, hauteur - marge_y, largeur - marge_x + 10, hauteur - marge_y, arrow=tk.LAST, fill=TEXT_MUTED, width=2)
        self.canvas_droite.create_line(marge_x, hauteur - marge_y, marge_x, marge_y - 10, arrow=tk.LAST, fill=TEXT_MUTED, width=2)

        valeurs = [data_mois[k] for k in cles_mois]
        val_max = max(valeurs) if max(valeurs) > 0 else 1
        plafond = val_max * 1.2 
        pas_x = zone_dessin_l / (len(cles_mois) - 1) if len(cles_mois) > 1 else zone_dessin_l / 2

        points = []
        for i, mois in enumerate(cles_mois):
            val = data_mois[mois]
            x = marge_x + i * pas_x if len(cles_mois) > 1 else marge_x + pas_x
            y = (hauteur - marge_y) - (val / plafond) * zone_dessin_h
            points.append((x, y))
            self.canvas_droite.create_text(x, y - 12, text=f"{val}", font=("Arial", 8, "bold"), fill=TEXT_COLOR)
            self.canvas_droite.create_text(x, hauteur - marge_y + 12, text=mois[:2], font=("Arial", 8), fill=TEXT_MUTED)

        for i in range(len(points)):
            x, y = points[i]
            if i > 0:
                self.canvas_droite.create_line(points[i-1][0], points[i-1][1], x, y, fill=ACCENT_HOVER, width=2)
            self.canvas_droite.create_oval(x - 4, y - 4, x + 4, y + 4, fill=ACCENT_COLOR, outline=SURFACE_COLOR, width=1)

    def _get_documents_dir(self):
        docs_dir = os.path.expanduser("~/Documents")
        if not os.path.exists(docs_dir):
            try:
                os.makedirs(docs_dir, exist_ok=True)
            except Exception:
                docs_dir = os.path.expanduser("~")
        return docs_dir

    def generer_modele_vierge(self):
        dossier_documents = self._get_documents_dir()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            initialdir=dossier_documents,
            initialfile="Modele_Releve.pdf", 
            title="Enregistrer le modèle vierge dans Documents"
        )
        if filepath: 
            self._creer_pdf(filepath, vierge=True)

    def exporter_pdf(self):
        if not self.donnees:
            messagebox.showwarning("Attention", "Aucune donnée à exporter.")
            return
            
        donnees_a_exporter = []
        total_kwh = 0.0
        total_euros = 0.0
        
        for d in self.donnees:
            if self.filtre_mois_courant == "Tous les mois" or d["date"].endswith(self.filtre_mois_courant):
                donnees_a_exporter.append(d)
                total_kwh += float(d.get("charge", 0))
                total_euros += float(d.get("cout_total", 0))
                
        if not donnees_a_exporter:
            messagebox.showwarning("Attention", "Aucune donnée correspondant à la période filtrée.")
            return

        nom_fichier = "Export_Releves.pdf" if self.filtre_mois_courant == "Tous les mois" else f"Export_Releves_{self.filtre_mois_courant.replace('/', '-')}.pdf"
        dossier_documents = self._get_documents_dir()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            initialdir=dossier_documents,
            initialfile=nom_fichier, 
            title="Exporter en PDF dans Documents"
        )
        if filepath: 
            self._creer_pdf(filepath, vierge=False, donnees=donnees_a_exporter, totaux=(total_kwh, total_euros), periode=self.filtre_mois_courant)

    def _creer_pdf(self, filepath, vierge, donnees=None, totaux=(0,0), periode=""):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_draw_color(220, 220, 220) 
        
        couleur_titre = (45, 56, 48)
        couleur_entete_fond = (156, 191, 163)
        couleur_entete_texte = (0, 0, 0)
        
        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(*couleur_titre)
        titre = "Relevé Manuel - Charge VE" if vierge else f"Historique des Relevés - {periode}"
        pdf.cell(200, 15, titre, 0, 1, 'C')
        pdf.ln(3)

        pdf.set_fill_color(*couleur_entete_fond)
        pdf.set_text_color(*couleur_entete_texte)
        pdf.set_font("Arial", 'B', 9)
        
        if vierge:
            pdf.cell(30, 10, "Date", 1, 0, 'C', fill=True)
            pdf.cell(25, 10, "Debut (%)", 1, 0, 'C', fill=True)
            pdf.cell(25, 10, "Fin (%)", 1, 0, 'C', fill=True)
            pdf.cell(40, 10, "Charge (kWh)", 1, 0, 'C', fill=True)
            pdf.cell(70, 10, "Kilometrage", 1, 1, 'C', fill=True)
        else:
            # Les largeurs ont été augmentées pour atteindre un total exact de 190 mm 
            # afin que le tableau remplisse bien l'espace et soit parfaitement centré.
            pdf.cell(25, 10, "Date", 1, 0, 'C', fill=True)
            pdf.cell(20, 10, "Debut", 1, 0, 'C', fill=True)
            pdf.cell(20, 10, "Fin", 1, 0, 'C', fill=True)
            pdf.cell(25, 10, "Charge", 1, 0, 'C', fill=True)
            pdf.cell(20, 10, "Prix kWh", 1, 0, 'C', fill=True)
            pdf.cell(40, 10, "Kilometrage", 1, 0, 'C', fill=True)
            pdf.cell(40, 10, "Cout Total", 1, 1, 'C', fill=True)

        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0) 
        
        fond_actuel = False
        
        if vierge:
            for _ in range(20):
                pdf.set_fill_color(*(230, 235, 232) if fond_actuel else (250, 252, 251))
                pdf.cell(30, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(25, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(25, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(40, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(70, 10, "", 1, 1, 'C', fill=True)
                fond_actuel = not fond_actuel
        else:
            for d in donnees:
                pdf.set_fill_color(*(230, 235, 232) if fond_actuel else (250, 252, 251))
                pdf.cell(25, 10, str(d.get("date", "")), 1, 0, 'C', fill=True)
                pdf.cell(20, 10, f"{d.get('debut_charge', 0):g}%", 1, 0, 'C', fill=True)
                pdf.cell(20, 10, f"{d.get('fin_charge', 0):g}%", 1, 0, 'C', fill=True)
                pdf.cell(25, 10, str(d.get("charge", "")), 1, 0, 'C', fill=True)
                pdf.cell(20, 10, str(d.get("prix_kwh", "")), 1, 0, 'C', fill=True)
                pdf.cell(40, 10, str(d.get("km", "")), 1, 0, 'C', fill=True)
                pdf.cell(40, 10, str(d.get("cout_total", "")), 1, 1, 'C', fill=True)
                fond_actuel = not fond_actuel
                
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(220, 220, 220)
            
            # Alignement géométrique de la ligne des totaux avec les colonnes supérieures :
            # Cellule 1 : Couvre "Date" (25) + "Debut" (20) + "Fin" (20) = 65
            pdf.cell(45, 10, "TOTAUX :", 1, 0, 'R', fill=True)
            
            # Cellule 2 : Couvre "Charge" (25)
            pdf.cell(25, 10, f"{totaux[0]:.2f} kWh", 1, 0, 'C', fill=True)
            
            # Cellule 3 : Espace vide qui couvre "Prix kWh" (20) + "Kilometrage" (40) = 60
            pdf.cell(10, 10, "", 1, 0, 'C', fill=True) 
            
            # Cellule 4 : Couvre "Cout Total" (40)
            pdf.cell(110, 10, f"{totaux[1]:.2f} Euro (Hors taxes)", 1, 1, 'C', fill=True)

        pdf.output(filepath)
        messagebox.showinfo("Succès", f"Fichier PDF généré : {os.path.basename(filepath)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReleveVEApp(root)
    root.mainloop()
