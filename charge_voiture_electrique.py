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
APP_VERSION = "v1.6.1"
APP_DATE = "Juillet 2026"
APP_AUTHOR = "Durand Joël"
APP_EMAIL = "rd66lago@gmail.com"  # <- Modifiez avec votre véritable adresse e-mail

# --- Fichiers ---
DB_FILE = os.path.expanduser("~/.local/share/ReleveVE/.releve_ve_data.db")
CONFIG_FILE = os.path.expanduser("~/.local/share/ReleveVE/.releve_ve_config.json")

# --- Thème Vert Menthe (Flat Design) ---
COLOR_MINT = "#e0f7fa"  
COLOR_BLUE = "#b3e5fc"  
BG_COLOR = "#f4fcfb"    

class ReleveVEApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} - {APP_VERSION}")
        self.root.geometry("1150x880")
        self.root.configure(bg=BG_COLOR)

        self.donnees = []
        self.id_edition = None
        self.prix_kwh_defaut = ""
        self.filtre_mois_courant = "Tous les mois"

        self.sauvegarde_automatique()
        self.charger_config()
        self.initialiser_bdd()
        
        # On crée le menu et l'interface AVANT de charger les données !
        self.creer_menu()
        self.creer_interface()
        self.charger_donnees()
        
        self.root.update()
        self.dessiner_graphiques()

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
        menubar = tk.Menu(self.root, bg=BG_COLOR, fg="black", bd=0, relief=tk.FLAT)
        
        # Menu Fichier
        menu_fichier = tk.Menu(menubar, tearoff=0, bg=BG_COLOR, fg="black", bd=0, relief=tk.FLAT)
        menu_fichier.add_command(label="Éditer Modèle Vierge PDF", command=self.generer_modele_vierge)
        menu_fichier.add_command(label="Exporter les données en PDF", command=self.exporter_pdf)
        menu_fichier.add_separator()
        menu_fichier.add_command(label="Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=menu_fichier)
        
        # Menu À Propos / Aide
        menu_aide = tk.Menu(menubar, tearoff=0, bg=BG_COLOR, fg="black", bd=0, relief=tk.FLAT)
        menu_aide.add_command(label="À propos de l'application...", command=self.afficher_a_propos)
        menubar.add_cascade(label="?", menu=menu_aide)

        self.root.config(menu=menubar)

    def afficher_a_propos(self):
        win_propos = tk.Toplevel(self.root)
        win_propos.title("À propos")
        win_propos.geometry("520x440")
        win_propos.configure(bg=BG_COLOR)
        win_propos.resizable(False, False)
        
        win_propos.transient(self.root)
        win_propos.grab_set()

        frame_head = tk.Frame(win_propos, bg=COLOR_MINT, pady=15)
        frame_head.pack(fill=tk.X)
        
        tk.Label(frame_head, text=APP_NAME, bg=COLOR_MINT, fg="#006064", font=("Arial", 14, "bold")).pack()
        tk.Label(frame_head, text=f"Version : {APP_VERSION}  -  {APP_DATE}", bg=COLOR_MINT, fg="black", font=("Arial", 10)).pack(pady=(5, 0))

        frame_desc = tk.Frame(win_propos, bg=BG_COLOR, padx=20, pady=15)
        frame_desc.pack(fill=tk.BOTH, expand=True)

        explication = (
            "Cette application permet d'enregistrer et d'analyser vos recharges "
            "de véhicule électrique en toute simplicité :\n\n"
            "  • Saisie du taux de charge initial et final (en %)\n"
            "  • Filtrage des relevés par mois avec statistiques adaptées\n"
            "  • Graphiques mensuels (courbe d'évolution et histogramme annuel horizontal)\n"
            "  • Exportation PDF automatique dans le dossier Documents\n"
            "  • Sauvegarde locale sécurisée dans votre répertoire personnel\n\n"
            "Astuce : Cliquez sur une ligne pour la modifier, ou faites un clic droit "
            "pour afficher le menu d'actions rapides !"
        )
        tk.Label(frame_desc, text=explication, bg=BG_COLOR, fg="black", font=("Arial", 10), justify=tk.LEFT, wraplength=460).pack(anchor="w")

        frame_foot = tk.Frame(win_propos, bg=COLOR_BLUE, pady=10)
        frame_foot.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Label(frame_foot, text=f"© {datetime.date.today().year} - {APP_AUTHOR} - Tous droits réservés.", bg=COLOR_BLUE, fg="black", font=("Arial", 9, "bold")).pack()
        tk.Label(frame_foot, text=f"Contact / Assistance : {APP_EMAIL}", bg=COLOR_BLUE, fg="black", font=("Arial", 9)).pack(pady=(3, 0))

    def creer_interface(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("Treeview", background="white", foreground="black", fieldbackground="white", borderwidth=0)
        style.map('Treeview', background=[('selected', COLOR_BLUE)], foreground=[('selected', 'black')])
        style.configure("Treeview.Heading", background=COLOR_MINT, foreground="black", font=("Arial", 10, "bold"), borderwidth=0)

        frame_stats = tk.Frame(self.root, bg=BG_COLOR, bd=0, highlightthickness=0)
        frame_stats.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        self.lbl_depense = tk.Label(frame_stats, text="Dépense totale : 0.00 €", bg=BG_COLOR, fg="#006064", font=("Arial", 12, "bold"))
        self.lbl_depense.pack(side=tk.LEFT, padx=10)
        
        self.lbl_cout_moyen = tk.Label(frame_stats, text="Coût moyen : 0.00 € / 100 km", bg=BG_COLOR, fg="#00838f", font=("Arial", 12, "bold"))
        self.lbl_cout_moyen.pack(side=tk.RIGHT, padx=10)

        frame_saisie = tk.Frame(self.root, bg=COLOR_MINT, bd=0, highlightthickness=0)
        frame_saisie.pack(fill=tk.X, padx=10, pady=15)

        entry_kwargs = {
            "bg": "white", 
            "fg": "black", 
            "insertbackground": "black", 
            "relief": tk.FLAT, 
            "bd": 0, 
            "highlightthickness": 0
        }

        # Date
        tk.Label(frame_saisie, text="Date :", bg=COLOR_MINT, fg="black").grid(row=0, column=0, padx=3, pady=15, sticky="e")
        self.ent_date = tk.Entry(frame_saisie, width=10, **entry_kwargs)
        self.ent_date.grid(row=0, column=1, padx=3, pady=15)
        self.ent_date.insert(0, datetime.date.today().strftime("%d/%m/%Y"))

        # Début de charge (%)
        tk.Label(frame_saisie, text="Début (%) :", bg=COLOR_MINT, fg="black").grid(row=0, column=2, padx=3, pady=15, sticky="e")
        self.ent_debut = tk.Entry(frame_saisie, width=6, **entry_kwargs)
        self.ent_debut.grid(row=0, column=3, padx=3, pady=15)

        # Fin de charge (%)
        tk.Label(frame_saisie, text="Fin (%) :", bg=COLOR_MINT, fg="black").grid(row=0, column=4, padx=3, pady=15, sticky="e")
        self.ent_fin = tk.Entry(frame_saisie, width=6, **entry_kwargs)
        self.ent_fin.grid(row=0, column=5, padx=3, pady=15)

        # Charge (kWh)
        tk.Label(frame_saisie, text="Charge (kWh) :", bg=COLOR_MINT, fg="black").grid(row=0, column=6, padx=3, pady=15, sticky="e")
        self.ent_charge = tk.Entry(frame_saisie, width=8, **entry_kwargs)
        self.ent_charge.grid(row=0, column=7, padx=3, pady=15)

        # Prix kWh (€)
        tk.Label(frame_saisie, text="Prix kWh (€) :", bg=COLOR_MINT, fg="black").grid(row=0, column=8, padx=3, pady=15, sticky="e")
        self.ent_prix_kwh = tk.Entry(frame_saisie, width=8, **entry_kwargs)
        self.ent_prix_kwh.grid(row=0, column=9, padx=3, pady=15)
        if self.prix_kwh_defaut:
            self.ent_prix_kwh.insert(0, self.prix_kwh_defaut)

        # Km total
        tk.Label(frame_saisie, text="Km total :", bg=COLOR_MINT, fg="black").grid(row=0, column=10, padx=3, pady=15, sticky="e")
        self.ent_km = tk.Entry(frame_saisie, width=10, **entry_kwargs)
        self.ent_km.grid(row=0, column=11, padx=3, pady=15)

        self.btn_ajouter = tk.Button(frame_saisie, text="Ajouter", bg=COLOR_BLUE, fg="black", relief=tk.FLAT, bd=0, highlightthickness=0, font=("Arial", 10, "bold"), command=self.valider_saisie)
        self.btn_ajouter.grid(row=0, column=12, padx=(10, 3), pady=15)

        # Bouton Annuler modification
        self.btn_annuler = tk.Button(frame_saisie, text="X", bg="#ef5350", fg="white", relief=tk.FLAT, bd=0, highlightthickness=0, font=("Arial", 10, "bold"), command=self.reinitialiser_formulaire)
        self.btn_annuler.grid(row=0, column=13, padx=(2, 10), pady=15)
        self.btn_annuler.grid_remove()

        # --- Barre de filtrage par mois ---
        frame_filtre = tk.Frame(self.root, bg=BG_COLOR)
        frame_filtre.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Label(frame_filtre, text="🔍 Filtrer par mois :", bg=BG_COLOR, fg="#006064", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(5, 5))
        
        self.combo_mois = ttk.Combobox(frame_filtre, state="readonly", width=15)
        self.combo_mois.pack(side=tk.LEFT, padx=5)
        self.combo_mois.bind("<<ComboboxSelected>>", self.sur_changement_filtre)

        btn_reset_filtre = tk.Button(frame_filtre, text="Voir tout", bg=COLOR_BLUE, fg="black", relief=tk.FLAT, bd=0, highlightthickness=0, font=("Arial", 9, "bold"), command=self.reset_filtre_mois)
        btn_reset_filtre.pack(side=tk.LEFT, padx=5)

        colonnes = ("date", "debut_charge", "fin_charge", "charge", "prix_kwh", "cout_total", "km", "conso_moyenne")
        self.tree = ttk.Treeview(self.root, columns=colonnes, show="headings", height=9)
        self.tree.heading("date", text="Date")
        self.tree.heading("debut_charge", text="Début (%)")
        self.tree.heading("fin_charge", text="Fin (%)")
        self.tree.heading("charge", text="Charge (kWh)")
        self.tree.heading("prix_kwh", text="Prix kWh (€)")
        self.tree.heading("cout_total", text="Coût Total (€)")
        self.tree.heading("km", text="Kilométrage")
        self.tree.heading("conso_moyenne", text="Conso (kWh/100km)")
        
        self.tree.column("date", width=85, anchor="center")
        self.tree.column("debut_charge", width=75, anchor="center")
        self.tree.column("fin_charge", width=75, anchor="center")
        self.tree.column("charge", width=90, anchor="center")
        self.tree.column("prix_kwh", width=85, anchor="center")
        self.tree.column("cout_total", width=95, anchor="center")
        self.tree.column("km", width=95, anchor="center")
        self.tree.column("conso_moyenne", width=130, anchor="center")
        
        self.tree.pack(fill=tk.X, padx=10, pady=5)

        # --- Événements sur le tableau ---
        self.tree.bind("<<TreeviewSelect>>", self.sur_selection_ligne)
        self.tree.bind("<Button-3>", self.sur_clic_droit)
        self.tree.bind("<Delete>", lambda e: self.supprimer_releve())

        # --- Menu contextuel ---
        self.menu_contextuel = tk.Menu(self.root, tearoff=0, bg="white", fg="black", relief=tk.FLAT)
        self.menu_contextuel.add_command(label="✏️ Modifier ce relevé", command=self.preparer_modification)
        self.menu_contextuel.add_command(label="🗑️ Supprimer ce relevé", command=self.supprimer_releve)

        # --- Zone des 2 Graphiques en bas ---
        frame_graphiques = tk.Frame(self.root, bg=BG_COLOR)
        frame_graphiques.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Graphique Gauche : Évolution mois par mois (Courbe)
        frame_gauche = tk.Frame(frame_graphiques, bg=BG_COLOR)
        frame_gauche.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        tk.Label(frame_gauche, text="Évolution de la conso. mois par mois (kWh/100km)", bg=BG_COLOR, fg="#006064", font=("Arial", 10, "bold")).pack(pady=(5, 2))
        self.canvas_courbe = tk.Canvas(frame_gauche, bg="white", height=220, bd=0, highlightthickness=0)
        self.canvas_courbe.pack(fill=tk.BOTH, expand=True)

        # Graphique Droite : Comparatif annuel en barres horizontales
        frame_droite = tk.Frame(frame_graphiques, bg=BG_COLOR)
        frame_droite.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        tk.Label(frame_droite, text=f"Comparatif annuel ({datetime.date.today().year})", bg=BG_COLOR, fg="#00838f", font=("Arial", 10, "bold")).pack(pady=(5, 2))
        self.canvas_barres = tk.Canvas(frame_droite, bg="white", height=220, bd=0, highlightthickness=0)
        self.canvas_barres.pack(fill=tk.BOTH, expand=True)
        
        self.canvas_courbe.bind("<Configure>", lambda e: self.dessiner_graphiques())

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
        # Sécurité pour éviter toute erreur si l'interface n'est pas encore créée
        if not hasattr(self, "combo_mois"):
            return
            
        mois_presents = set()
        for d in self.donnees:
            try:
                mois_presents.add(d["date"][3:])
            except Exception:
                pass
        
        liste_mois = ["Tous les mois"] + sorted(list(mois_presents))
        self.combo_mois["values"] = liste_mois
        if self.filtre_mois_courant not in liste_mois:
            self.filtre_mois_courant = "Tous les mois"
        self.combo_mois.set(self.filtre_mois_courant)

    def reinitialiser_formulaire(self):
        self.id_edition = None
        self.btn_ajouter.config(text="Ajouter", bg=COLOR_BLUE)
        self.btn_annuler.grid_remove()
        
        self.ent_date.delete(0, tk.END)
        self.ent_date.insert(0, datetime.date.today().strftime("%d/%m/%Y"))
        self.ent_debut.delete(0, tk.END)
        self.ent_fin.delete(0, tk.END)
        self.ent_charge.delete(0, tk.END)
        self.ent_km.delete(0, tk.END)
        
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
        self.ent_km.insert(0, valeurs[6])
        
        self.btn_ajouter.config(text="Valider modif.", bg="#ffeb3b")
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

    def actualiser_statistiques(self, donnees_affichees):
        if not donnees_affichees:
            self.lbl_depense.config(text="Dépense totale : 0.00 €")
            self.lbl_cout_moyen.config(text="Coût moyen : -- € / 100 km")
            return

        depense_totale = sum(d.get("cout_total", 0) for d in donnees_affichees)
        self.lbl_depense.config(text=f"Dépense totale : {depense_totale:.2f} €")

        if len(donnees_affichees) > 1:
            km_total = float(donnees_affichees[-1]["km"]) - float(donnees_affichees[0]["km"])
            depense_utile = sum(d.get("cout_total", 0) for d in donnees_affichees[1:])
            
            if km_total > 0:
                cout_100km = (depense_utile / km_total) * 100
                self.lbl_cout_moyen.config(text=f"Coût moyen : {cout_100km:.2f} € / 100 km")
            else:
                self.lbl_cout_moyen.config(text="Coût moyen : -- € / 100 km")
        else:
            self.lbl_cout_moyen.config(text="Coût moyen : -- € / 100 km")

    def afficher_donnees(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        donnees_filtrees = []
        for d in self.donnees:
            if self.filtre_mois_courant == "Tous les mois" or d["date"].endswith(self.filtre_mois_courant):
                donnees_filtrees.append(d)
                self.tree.insert("", tk.END, iid=str(d["id"]), values=(
                    d["date"], 
                    f"{d.get('debut_charge', 0):g}%", 
                    f"{d.get('fin_charge', 0):g}%", 
                    d["charge"], 
                    d["prix_kwh"], 
                    d.get("cout_total", ""), 
                    d["km"], 
                    d.get("conso_100km", "")
                ))
        
        self.actualiser_statistiques(donnees_filtrees)
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
        self._dessiner_graphique_courbe_mensuelle()
        self._dessiner_graphique_barres_annuelles()

    def _dessiner_graphique_courbe_mensuelle(self):
        self.canvas_courbe.delete("all")
        data_mois = self._calculer_consommation_par_mois()
        cles_mois = list(data_mois.keys())

        if len(cles_mois) < 1:
            self.canvas_courbe.create_text(250, 110, text="Ajoutez des relevés pour voir la courbe", fill="#888888", font=("Arial", 11, "italic"))
            return

        largeur, hauteur = self.canvas_courbe.winfo_width(), self.canvas_courbe.winfo_height()
        if largeur <= 1: largeur = 500
        if hauteur <= 1: hauteur = 220

        marge_x, marge_y = 40, 30
        zone_dessin_l, zone_dessin_h = largeur - 2 * marge_x, hauteur - 2 * marge_y

        self.canvas_courbe.create_line(marge_x, hauteur - marge_y, largeur - marge_x + 10, hauteur - marge_y, arrow=tk.LAST, fill="black", width=2)
        self.canvas_courbe.create_line(marge_x, hauteur - marge_y, marge_x, marge_y - 10, arrow=tk.LAST, fill="black", width=2)

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
            self.canvas_courbe.create_text(x, y - 12, text=f"{val}", font=("Arial", 8, "bold"), fill="#006064")
            self.canvas_courbe.create_text(x, hauteur - marge_y + 12, text=mois[:2], font=("Arial", 8), fill="black")

        for i in range(len(points)):
            x, y = points[i]
            if i > 0:
                self.canvas_courbe.create_line(points[i-1][0], points[i-1][1], x, y, fill="#00acc1", width=2)
            self.canvas_courbe.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#00838f", outline="white", width=1)

    def _dessiner_graphique_barres_annuelles(self):
        self.canvas_barres.delete("all")
        data_mois = self._calculer_consommation_par_mois()
        annee_courante = str(datetime.date.today().year)
        
        mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Juil", "Aout", "Sept", "Oct", "Nov", "Déc"]
        valeurs_annee = []
        
        for idx in range(1, 13):
            cle = f"{idx:02d}/{annee_courante}"
            valeurs_annee.append(data_mois.get(cle, 0))

        largeur, hauteur = self.canvas_barres.winfo_width(), self.canvas_barres.winfo_height()
        if largeur <= 1: largeur = 500
        if hauteur <= 1: hauteur = 220

        marge_gauche, marge_droite = 35, 45
        marge_haut, marge_bas = 15, 20
        
        zone_dessin_l = largeur - marge_gauche - marge_droite
        zone_dessin_h = hauteur - marge_haut - marge_bas

        self.canvas_barres.create_line(marge_gauche, hauteur - marge_bas, largeur - marge_droite + 15, hauteur - marge_bas, arrow=tk.LAST, fill="black", width=2)
        self.canvas_barres.create_line(marge_gauche, hauteur - marge_bas, marge_gauche, marge_haut - 10, arrow=tk.LAST, fill="black", width=2)

        val_max = max(valeurs_annee) if max(valeurs_annee) > 0 else 1
        plafond = val_max * 1.25
        hauteur_barre = (zone_dessin_h / 12) * 0.65
        espacement = (zone_dessin_h / 12)

        for i in range(12):
            val = valeurs_annee[i]
            y_centre = marge_haut + i * espacement + espacement / 2
            
            self.canvas_barres.create_text(marge_gauche - 15, y_centre, text=mois_noms[i], font=("Arial", 8, "bold"), fill="black")
            
            if val > 0:
                l_barre = (val / plafond) * zone_dessin_l
                x0 = marge_gauche + 1
                y0 = y_centre - hauteur_barre / 2
                x1 = marge_gauche + l_barre
                y1 = y_centre + hauteur_barre / 2
                
                self.canvas_barres.create_rectangle(x0, y0, x1, y1, fill="#80deea", outline="#00838f", width=1)
                self.canvas_barres.create_text(x1 + 18, y_centre, text=f"{val}", font=("Arial", 8, "bold"), fill="#006064")

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
        dossier_documents = self._get_documents_dir()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            initialdir=dossier_documents,
            initialfile="Export_Releves.pdf", 
            title="Exporter en PDF dans Documents"
        )
        if filepath: 
            self._creer_pdf(filepath, vierge=False)

    def _creer_pdf(self, filepath, vierge):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_draw_color(220, 220, 220) 
        
        couleur_titre = (0, 131, 143)
        couleur_entete_fond = (179, 229, 252) 
        couleur_entete_texte = (0, 0, 0)

        pdf.set_font("Arial", 'B', 16)
        pdf.set_text_color(*couleur_titre)
        titre = "Relevé Manuel - Charge VE" if vierge else "Historique des Relevés de Charge VE"
        pdf.cell(190, 15, titre, 0, 1, 'C')
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
            pdf.cell(20, 10, "Date", 1, 0, 'C', fill=True)
            pdf.cell(18, 10, "Debut", 1, 0, 'C', fill=True)
            pdf.cell(18, 10, "Fin", 1, 0, 'C', fill=True)
            pdf.cell(20, 10, "Charge", 1, 0, 'C', fill=True)
            pdf.cell(20, 10, "Prix kWh", 1, 0, 'C', fill=True)
            pdf.cell(22, 10, "Cout Total", 1, 0, 'C', fill=True)
            pdf.cell(34, 10, "Kilometrage", 1, 0, 'C', fill=True)
            pdf.cell(38, 10, "Conso (kWh/100)", 1, 1, 'C', fill=True)

        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(0, 0, 0) 
        
        fond_actuel = False
        
        if vierge:
            for _ in range(20):
                pdf.set_fill_color(*(235, 248, 250) if fond_actuel else (255, 255, 255))
                pdf.cell(30, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(25, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(25, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(40, 10, "", 1, 0, 'C', fill=True)
                pdf.cell(70, 10, "", 1, 1, 'C', fill=True)
                fond_actuel = not fond_actuel
        else:
            for d in self.donnees:
                pdf.set_fill_color(*(235, 248, 250) if fond_actuel else (255, 255, 255))
                pdf.cell(20, 10, str(d.get("date", "")), 1, 0, 'C', fill=True)
                pdf.cell(18, 10, f"{d.get('debut_charge', 0):g}%", 1, 0, 'C', fill=True)
                pdf.cell(18, 10, f"{d.get('fin_charge', 0):g}%", 1, 0, 'C', fill=True)
                pdf.cell(20, 10, str(d.get("charge", "")), 1, 0, 'C', fill=True)
                pdf.cell(20, 10, str(d.get("prix_kwh", "")), 1, 0, 'C', fill=True)
                pdf.cell(22, 10, str(d.get("cout_total", "")), 1, 0, 'C', fill=True)
                pdf.cell(34, 10, str(d.get("km", "")), 1, 0, 'C', fill=True)
                pdf.cell(38, 10, str(d.get("conso_100km", "")), 1, 1, 'C', fill=True)
                fond_actuel = not fond_actuel

        pdf.output(filepath)
        messagebox.showinfo("Succès", f"Fichier PDF généré : {os.path.basename(filepath)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReleveVEApp(root)
    root.mainloop()
