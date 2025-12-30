"""
GEN-DOC - Interface Graphique Améliorée
Avec prévisualisation des données d'entrée et des PDF générés
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from pathlib import Path
from typing import Optional
import threading
import webbrowser
import subprocess
import logging
import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_reader import DataReader
from core.validators import DataValidator, DocumentType, validate_data
from core.calculators import CalculatorFacture, CalculatorPaie
from core.pdf_generator import InvoiceGenerator, PayslipGenerator
from database.logs import get_next_invoice_number, log_document, get_db_manager
from config.settings import COMPANY_INFO, OUTPUT_DIR
from gui.settings import SettingsWindow, get_company_info

logger = logging.getLogger("GEN-DOC.GUI")

# Configuration du thème
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DataPreviewFrame(ctk.CTkFrame):
    """Frame pour prévisualiser les données d'entrée."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=10)

        # Titre
        self.title = ctk.CTkLabel(
            self,
            text="📊 Aperçu des données",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.title.pack(anchor="w", padx=10, pady=(10, 5))

        # Info label
        self.info_label = ctk.CTkLabel(
            self,
            text="Sélectionnez un fichier pour voir l'aperçu",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        self.info_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Frame pour le tableau avec scrollbar
        self.table_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Treeview pour afficher les données
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=25,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#1f538d",
            foreground="white",
            font=("Helvetica", 10, "bold"),
        )

        # Scrollbars
        self.scroll_y = ttk.Scrollbar(self.table_frame, orient="vertical")
        self.scroll_x = ttk.Scrollbar(self.table_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            self.table_frame,
            style="Custom.Treeview",
            yscrollcommand=self.scroll_y.set,
            xscrollcommand=self.scroll_x.set,
            height=8,  # Limiter à 8 lignes visibles
        )

        self.scroll_y.config(command=self.tree.yview)
        self.scroll_x.config(command=self.tree.xview)

        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def load_data(self, df):
        """Charge les données dans le tableau."""
        # Effacer l'ancien contenu
        self.tree.delete(*self.tree.get_children())

        # Configurer les colonnes
        columns = list(df.columns)
        self.tree["columns"] = columns
        self.tree["show"] = "headings"

        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=100, minwidth=80)

        # Ajouter les lignes
        for idx, row in df.iterrows():
            values = [str(v)[:30] for v in row.values]  # Tronquer les valeurs longues
            self.tree.insert("", "end", values=values)

        self.info_label.configure(text=f"✅ {len(df)} lignes chargées")

    def clear(self):
        """Efface le tableau."""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []
        self.info_label.configure(text="Sélectionnez un fichier pour voir l'aperçu")


class OutputPreviewFrame(ctk.CTkFrame):
    """Frame pour prévisualiser les documents générés."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=10)
        self.generated_files = []

        # Titre
        self.title = ctk.CTkLabel(
            self,
            text="📄 Documents générés",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.title.pack(anchor="w", padx=10, pady=(10, 5))

        # Liste des fichiers
        self.files_frame = ctk.CTkScrollableFrame(self, height=150)
        self.files_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Message vide
        self.empty_label = ctk.CTkLabel(
            self.files_frame,
            text="Aucun document généré",
            text_color=("gray50", "gray60"),
        )
        self.empty_label.pack(pady=20)

        # Boutons d'action
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.btn_open_folder = ctk.CTkButton(
            self.btn_frame,
            text="📂 Ouvrir dossier",
            command=self.open_folder,
            width=120,
            height=30,
        )
        self.btn_open_folder.pack(side="left", padx=5)

        self.btn_open_last = ctk.CTkButton(
            self.btn_frame,
            text="📄 Ouvrir dernier",
            command=self.open_last,
            width=120,
            height=30,
            state="disabled",
        )
        self.btn_open_last.pack(side="left", padx=5)

    def add_file(self, filepath: Path, doc_type: str, client_name: str, amount: float):
        """Ajoute un fichier à la liste."""
        self.empty_label.pack_forget()

        file_frame = ctk.CTkFrame(self.files_frame, fg_color=("gray85", "gray20"))
        file_frame.pack(fill="x", pady=2)

        # Icône + Nom
        icon = "📄" if doc_type == "facture" else "💰"
        name_label = ctk.CTkLabel(
            file_frame,
            text=f"{icon} {filepath.name}",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        )
        name_label.pack(side="left", padx=10, pady=5)

        # Montant
        amount_label = ctk.CTkLabel(
            file_frame,
            text=f"{amount:,.2f} €".replace(",", " "),
            font=ctk.CTkFont(size=11),
            text_color=("#10b981", "#10b981"),
        )
        amount_label.pack(side="right", padx=10, pady=5)

        # Bouton ouvrir
        btn = ctk.CTkButton(
            file_frame,
            text="Ouvrir",
            width=60,
            height=24,
            command=lambda p=filepath: self.open_file(p),
        )
        btn.pack(side="right", padx=5, pady=5)

        self.generated_files.append(filepath)
        self.btn_open_last.configure(state="normal")

    def open_file(self, filepath: Path):
        """Ouvre un fichier PDF."""
        if sys.platform == "linux":
            subprocess.run(["xdg-open", str(filepath)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(filepath)])
        else:
            os.startfile(str(filepath))

    def open_folder(self):
        """Ouvre le dossier de sortie."""
        OUTPUT_DIR.mkdir(exist_ok=True)
        if sys.platform == "linux":
            subprocess.run(["xdg-open", str(OUTPUT_DIR)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(OUTPUT_DIR)])
        else:
            os.startfile(str(OUTPUT_DIR))

    def open_last(self):
        """Ouvre le dernier fichier généré."""
        if self.generated_files:
            self.open_file(self.generated_files[-1])

    def clear(self):
        """Efface la liste."""
        for widget in self.files_frame.winfo_children():
            if widget != self.empty_label:
                widget.destroy()
        self.empty_label.pack(pady=20)
        self.generated_files = []
        self.btn_open_last.configure(state="disabled")


class GENDOCApp(ctk.CTk):
    """Application principale GEN-DOC."""

    def __init__(self):
        super().__init__()

        self.title("GEN-DOC - Générateur de Documents")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        self.selected_file: Optional[str] = None
        self.document_type: str = "facture"
        self.current_df = None

        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur."""
        # Configuration du grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # En-tête
        self._create_header()

        # Panneau gauche (Contrôles)
        self._create_left_panel()

        # Panneau droit (Prévisualisations)
        self._create_right_panel()

    def _create_header(self):
        """Crée l'en-tête."""
        header = ctk.CTkFrame(self, corner_radius=0, height=60)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Logo et titre
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            title_frame,
            text="📑 GEN-DOC",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame,
            text="  •  Générateur de documents professionnels",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60"),
        ).pack(side="left", padx=10)

        # Bouton Settings
        self.btn_settings = ctk.CTkButton(
            header,
            text="⚙️ Paramètres",
            command=self.open_settings,
            width=120,
            height=35,
            fg_color="transparent",
            border_width=1,
        )
        self.btn_settings.pack(side="right", padx=20, pady=10)

    def _create_left_panel(self):
        """Panneau de contrôle gauche."""
        left = ctk.CTkFrame(self, corner_radius=0)
        left.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)

        # === Section Import ===
        import_frame = ctk.CTkFrame(left, corner_radius=10)
        import_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            import_frame,
            text="📁 Import de fichier",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # Bouton sélection fichier
        self.btn_select = ctk.CTkButton(
            import_frame,
            text="Sélectionner un fichier CSV/Excel",
            command=self.select_file,
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.btn_select.pack(fill="x", padx=15, pady=10)

        # Label fichier sélectionné
        self.file_label = ctk.CTkLabel(
            import_frame,
            text="Aucun fichier sélectionné",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        self.file_label.pack(anchor="w", padx=15, pady=(0, 10))

        # === Section Type de document ===
        type_frame = ctk.CTkFrame(left, corner_radius=10)
        type_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            type_frame,
            text="📋 Type de document",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.type_var = ctk.StringVar(value="facture")

        types = [
            ("facture", "📄 Facture"),
            ("fiche_paie", "💰 Fiche de paie"),
        ]

        for value, label in types:
            ctk.CTkRadioButton(
                type_frame,
                text=label,
                variable=self.type_var,
                value=value,
                command=self.on_type_change,
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=20, pady=5)

        ctk.CTkLabel(type_frame, text="").pack(pady=5)  # Spacer

        # === Section Génération ===
        gen_frame = ctk.CTkFrame(left, corner_radius=10)
        gen_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            gen_frame,
            text="⚡ Génération",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # Bouton Générer
        self.btn_generate = ctk.CTkButton(
            gen_frame,
            text="🚀 GÉNÉRER LES DOCUMENTS",
            command=self.generate_documents,
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            state="disabled",
        )
        self.btn_generate.pack(fill="x", padx=15, pady=15)

        # Barre de progression
        self.progress = ctk.CTkProgressBar(gen_frame)
        self.progress.pack(fill="x", padx=15, pady=(0, 10))
        self.progress.set(0)

        # Status
        self.status_label = ctk.CTkLabel(
            gen_frame,
            text="En attente d'un fichier...",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
        )
        self.status_label.pack(anchor="w", padx=15, pady=(0, 10))

        # === Logs ===
        log_frame = ctk.CTkFrame(left, corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            log_frame,
            text="📝 Journal",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.log_text = ctk.CTkTextbox(log_frame, height=150, font=ctk.CTkFont(size=10))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _create_right_panel(self):
        """Panneau de prévisualisation droit."""
        right = ctk.CTkFrame(self, corner_radius=0)
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right.grid_columnconfigure(0, weight=1)
        # Ne pas donner de weight aux rows pour éviter l'expansion

        # Prévisualisation des données d'entrée (hauteur fixe)
        self.data_preview = DataPreviewFrame(right, height=280)
        self.data_preview.pack(fill="x", padx=5, pady=5)
        self.data_preview.pack_propagate(False)  # Empêcher l'expansion

        # Prévisualisation des documents générés
        self.output_preview = OutputPreviewFrame(right, height=280)
        self.output_preview.pack(fill="x", padx=5, pady=5)
        self.output_preview.pack_propagate(False)

    def log(self, message: str, level: str = "info"):
        """Ajoute un message au journal."""
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        self.log_text.insert("end", f"{icons.get(level, '')} {message}\n")
        self.log_text.see("end")

    def select_file(self):
        """Sélectionne un fichier."""
        filetypes = [
            ("Fichiers de données", "*.csv *.xlsx *.xls"),
            ("CSV", "*.csv"),
            ("Excel", "*.xlsx *.xls"),
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        """Charge et affiche le fichier."""
        self.selected_file = filepath
        filename = Path(filepath).name

        try:
            # Lire le fichier
            reader = DataReader(filepath)
            self.current_df = reader.read()

            # Mettre à jour l'UI
            self.file_label.configure(text=f"✅ {filename}", text_color=("#10b981", "#10b981"))
            self.btn_generate.configure(state="normal")
            self.status_label.configure(text=f"Prêt à générer ({len(self.current_df)} lignes)")

            # Afficher l'aperçu
            self.data_preview.load_data(self.current_df)

            # Valider
            doc_type = DocumentType(self.type_var.get())
            is_valid, results = validate_data(self.current_df, doc_type)

            if is_valid:
                self.log(f"Fichier chargé : {filename} ({len(self.current_df)} lignes)", "success")
            else:
                self.log(f"Attention : erreurs de validation", "warning")
                for r in results:
                    for e in r.errors:
                        self.log(f"  {e}", "error")

        except Exception as e:
            self.log(f"Erreur : {e}", "error")
            self.file_label.configure(text=f"❌ Erreur", text_color=("#ef4444", "#ef4444"))
            self.btn_generate.configure(state="disabled")

    def on_type_change(self):
        """Appelé quand le type change."""
        self.document_type = self.type_var.get()
        self.log(f"Type sélectionné : {self.document_type}", "info")

        # Revalider si un fichier est chargé
        if self.current_df is not None:
            doc_type = DocumentType(self.document_type)
            is_valid, _ = validate_data(self.current_df, doc_type)
            if not is_valid:
                self.log("⚠️ Le fichier ne correspond pas au type sélectionné", "warning")

    def generate_documents(self):
        """Lance la génération."""
        if not self.selected_file or self.current_df is None:
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un fichier.")
            return

        # Désactiver le bouton
        self.btn_generate.configure(state="disabled", text="⏳ Génération...")
        self.progress.set(0)
        self.output_preview.clear()

        # Lancer dans un thread
        thread = threading.Thread(target=self._generate_worker)
        thread.start()

    def _generate_worker(self):
        """Worker de génération."""
        try:
            from datetime import datetime

            df = self.current_df
            doc_type = self.type_var.get()

            self.log("Démarrage de la génération...", "info")

            if doc_type == "facture":
                self._generate_invoices(df)
            else:
                self._generate_payslips(df)

            self.progress.set(1)
            self.status_label.configure(text="✅ Génération terminée !")
            self.log("Génération terminée avec succès !", "success")

        except Exception as e:
            self.log(f"Erreur : {e}", "error")
            self.status_label.configure(text="❌ Erreur de génération")

        finally:
            self.btn_generate.configure(state="normal", text="🚀 GÉNÉRER LES DOCUMENTS")

    def _generate_invoices(self, df):
        """Génère les factures."""
        from datetime import datetime

        grouped = df.groupby(["client_nom", "client_adresse", "client_code_postal", "client_ville"])
        total_groups = len(grouped)
        generator = InvoiceGenerator()

        for idx, ((client_nom, client_adresse, cp, ville), group) in enumerate(grouped):
            invoice_number = get_next_invoice_number()

            client_info = {
                "nom": client_nom,
                "adresse": client_adresse,
                "code_postal": cp,
                "ville": ville,
                "siret": group["client_siret"].iloc[0] if "client_siret" in group.columns else "",
                "email": group["client_email"].iloc[0] if "client_email" in group.columns else "",
            }

            calculator = CalculatorFacture.from_dataframe(group)
            totaux = calculator.to_dict()

            pdf_path = generator.generate(
                invoice_number=invoice_number,
                client_info=client_info,
                lignes=totaux["lignes"],
                totaux=totaux,
                date_facture=datetime.now(),
            )

            log_document(
                document_type="facture",
                document_number=invoice_number,
                filename=str(pdf_path),
                client_name=client_nom,
                total_amount=totaux["total_ttc"],
                source_file=self.selected_file,
            )

            # Mise à jour UI via after() pour thread-safety
            progress_val = (idx + 1) / total_groups
            self.after(0, lambda p=progress_val: self.progress.set(p))
            self.after(0, lambda path=pdf_path, name=client_nom, ttc=totaux["total_ttc"]: 
                       self.output_preview.add_file(path, "facture", name, ttc))
            self.after(0, lambda num=invoice_number, nom=client_nom: 
                       self.log(f"✓ {num} → {nom}", "success"))

    def _generate_payslips(self, df):
        """Génère les fiches de paie."""
        from datetime import datetime

        generator = PayslipGenerator()
        period = datetime.now().strftime("%B %Y").capitalize()
        total = len(df)

        for idx, (_, row) in enumerate(df.iterrows()):
            salaire_brut = float(row["salaire_brut"])
            calculator = CalculatorPaie(
                salaire_brut=salaire_brut,
                heures_travaillees=float(row.get("heures_travaillees", 151.67)),
            )
            salaire_data = calculator.to_dict()

            salarie_info = {
                "nom": row["salarie_nom"],
                "prenom": row["salarie_prenom"],
                "matricule": row.get("salarie_matricule", ""),
                "poste": row["poste"],
                "date_embauche": row.get("date_embauche", ""),
            }

            pdf_path = generator.generate(
                salarie_info=salarie_info,
                periode=period,
                salaire_data=salaire_data,
                cotisations=salaire_data["cotisations"],
            )

            # Mise à jour UI via after() pour thread-safety
            progress_val = (idx + 1) / total
            name = f"{salarie_info['prenom']} {salarie_info['nom']}"
            net = salaire_data["salaire_net_avant_impot"]
            
            self.after(0, lambda p=progress_val: self.progress.set(p))
            self.after(0, lambda path=pdf_path, n=name, amount=net: 
                       self.output_preview.add_file(path, "fiche_paie", n, amount))
            self.after(0, lambda n=name: self.log(f"✓ Fiche de paie → {n}", "success"))

    def open_settings(self):
        """Ouvre la fenêtre des paramètres."""
        SettingsWindow(self, on_save_callback=self._on_settings_saved)
    
    def _on_settings_saved(self, settings):
        """Appelé quand les paramètres sont sauvegardés."""
        self.log("Paramètres mis à jour", "success")

def run_app():
    """Lance l'application."""
    app = GENDOCApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()
