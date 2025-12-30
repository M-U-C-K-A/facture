"""
GEN-DOC - Panneau de Paramètres
Permet de modifier les informations de l'entreprise, les couleurs et le logo.
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
from pathlib import Path
import json
import shutil
import logging

logger = logging.getLogger("GEN-DOC.Settings")

# Chemin du fichier de configuration utilisateur
CONFIG_FILE = Path(__file__).parent.parent / "config" / "user_settings.json"
LOGO_DIR = Path(__file__).parent.parent / "templates" / "assets"


class SettingsWindow(ctk.CTkToplevel):
    """Fenêtre de paramètres."""
    
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        
        self.title("⚙️ Paramètres")
        self.geometry("600x700")
        self.resizable(False, False)
        
        self.on_save_callback = on_save_callback
        self.settings = self._load_settings()
        
        # Centrer la fenêtre
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
    
    def _load_settings(self) -> dict:
        """Charge les paramètres depuis le fichier JSON."""
        default_settings = {
            "company": {
                "nom": "Votre Entreprise",
                "adresse": "123 Rue de l'Exemple",
                "code_postal": "75001",
                "ville": "Paris",
                "siret": "123 456 789 00012",
                "tva_intracom": "FR12345678901",
                "telephone": "+33 1 23 45 67 89",
                "email": "contact@votreentreprise.fr",
                "iban": "",
                "bic": "",
                "capital": "10000",
                "rcs": "Paris",
            },
            "colors": {
                "primary": "#1e40af",
                "accent": "#10b981",
            },
            "logo_path": "",
        }
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Fusionner avec les valeurs par défaut
                    for key in default_settings:
                        if key not in loaded:
                            loaded[key] = default_settings[key]
                    return loaded
            except Exception as e:
                logger.error(f"Erreur chargement settings: {e}")
        
        return default_settings
    
    def _save_settings(self):
        """Sauvegarde les paramètres dans le fichier JSON."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
        
        logger.info("Paramètres sauvegardés")
    
    def _create_ui(self):
        """Crée l'interface."""
        # Scrollable frame
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === Section Entreprise ===
        self._create_section("🏢 Informations Entreprise")
        
        self.entries = {}
        fields = [
            ("nom", "Nom de l'entreprise"),
            ("adresse", "Adresse"),
            ("code_postal", "Code postal"),
            ("ville", "Ville"),
            ("siret", "SIRET"),
            ("tva_intracom", "N° TVA Intracommunautaire"),
            ("telephone", "Téléphone"),
            ("email", "Email"),
            ("iban", "IBAN (pour QR Code)"),
            ("bic", "BIC"),
            ("capital", "Capital social (€)"),
            ("rcs", "RCS"),
        ]
        
        for key, label in fields:
            self._create_field(key, label, self.settings["company"].get(key, ""))
        
        # === Section Couleurs ===
        self._create_section("🎨 Palette de Couleurs")
        
        colors_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        colors_frame.pack(fill="x", padx=10, pady=5)
        
        # Couleur principale
        primary_frame = ctk.CTkFrame(colors_frame, fg_color="transparent")
        primary_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(primary_frame, text="Couleur principale:", width=150, anchor="w").pack(side="left")
        
        self.primary_color = self.settings["colors"].get("primary", "#1e40af")
        self.primary_preview = ctk.CTkButton(
            primary_frame,
            text="",
            width=40,
            height=30,
            fg_color=self.primary_color,
            hover_color=self.primary_color,
            command=lambda: self._pick_color("primary"),
        )
        self.primary_preview.pack(side="left", padx=5)
        
        self.primary_entry = ctk.CTkEntry(primary_frame, width=100)
        self.primary_entry.insert(0, self.primary_color)
        self.primary_entry.pack(side="left", padx=5)
        
        # Couleur accent
        accent_frame = ctk.CTkFrame(colors_frame, fg_color="transparent")
        accent_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(accent_frame, text="Couleur accent:", width=150, anchor="w").pack(side="left")
        
        self.accent_color = self.settings["colors"].get("accent", "#10b981")
        self.accent_preview = ctk.CTkButton(
            accent_frame,
            text="",
            width=40,
            height=30,
            fg_color=self.accent_color,
            hover_color=self.accent_color,
            command=lambda: self._pick_color("accent"),
        )
        self.accent_preview.pack(side="left", padx=5)
        
        self.accent_entry = ctk.CTkEntry(accent_frame, width=100)
        self.accent_entry.insert(0, self.accent_color)
        self.accent_entry.pack(side="left", padx=5)
        
        # === Section Logo ===
        self._create_section("🖼️ Logo")
        
        logo_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        logo_frame.pack(fill="x", padx=10, pady=10)
        
        self.logo_label = ctk.CTkLabel(
            logo_frame,
            text=self._get_logo_status(),
            anchor="w",
        )
        self.logo_label.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(
            logo_frame,
            text="📁 Importer",
            width=100,
            command=self._import_logo,
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            logo_frame,
            text="🗑️ Supprimer",
            width=100,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._remove_logo,
        ).pack(side="right", padx=5)
        
        # === Boutons d'action ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            btn_frame,
            text="💾 Sauvegarder",
            command=self._on_save,
            fg_color="#10b981",
            hover_color="#059669",
            height=40,
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            command=self.destroy,
            fg_color="transparent",
            border_width=1,
            height=40,
        ).pack(side="right", padx=5)
    
    def _create_section(self, title: str):
        """Crée un titre de section."""
        ctk.CTkLabel(
            self.scroll,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(15, 5))
    
    def _create_field(self, key: str, label: str, value: str):
        """Crée un champ de saisie."""
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(frame, text=label, width=180, anchor="w").pack(side="left")
        
        entry = ctk.CTkEntry(frame, width=300)
        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)
        
        self.entries[key] = entry
    
    def _pick_color(self, color_type: str):
        """Ouvre le sélecteur de couleur."""
        current = self.primary_color if color_type == "primary" else self.accent_color
        color = colorchooser.askcolor(color=current, title="Choisir une couleur")
        
        if color[1]:
            if color_type == "primary":
                self.primary_color = color[1]
                self.primary_preview.configure(fg_color=color[1], hover_color=color[1])
                self.primary_entry.delete(0, "end")
                self.primary_entry.insert(0, color[1])
            else:
                self.accent_color = color[1]
                self.accent_preview.configure(fg_color=color[1], hover_color=color[1])
                self.accent_entry.delete(0, "end")
                self.accent_entry.insert(0, color[1])
    
    def _get_logo_status(self) -> str:
        """Retourne le statut du logo."""
        logo_path = LOGO_DIR / "logo.png"
        if logo_path.exists():
            return f"✅ Logo installé : {logo_path.name}"
        return "❌ Aucun logo"
    
    def _import_logo(self):
        """Importe un logo."""
        filetypes = [
            ("Images", "*.png *.jpg *.jpeg *.svg"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
        ]
        filepath = filedialog.askopenfilename(filetypes=filetypes)
        
        if filepath:
            try:
                LOGO_DIR.mkdir(parents=True, exist_ok=True)
                dest = LOGO_DIR / "logo.png"
                shutil.copy(filepath, dest)
                self.logo_label.configure(text=self._get_logo_status())
                self.settings["logo_path"] = str(dest)
                messagebox.showinfo("Succès", "Logo importé avec succès !")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible d'importer le logo : {e}")
    
    def _remove_logo(self):
        """Supprime le logo."""
        logo_path = LOGO_DIR / "logo.png"
        if logo_path.exists():
            logo_path.unlink()
            self.logo_label.configure(text=self._get_logo_status())
            self.settings["logo_path"] = ""
            messagebox.showinfo("Succès", "Logo supprimé")
    
    def _on_save(self):
        """Sauvegarde les paramètres."""
        # Récupérer les valeurs des champs
        for key, entry in self.entries.items():
            self.settings["company"][key] = entry.get()
        
        # Couleurs
        self.settings["colors"]["primary"] = self.primary_entry.get()
        self.settings["colors"]["accent"] = self.accent_entry.get()
        
        # Sauvegarder
        self._save_settings()
        
        # Mettre à jour le CSS
        self._update_css_colors()
        
        # Callback
        if self.on_save_callback:
            self.on_save_callback(self.settings)
        
        messagebox.showinfo("Succès", "Paramètres sauvegardés !")
        self.destroy()
    
    def _update_css_colors(self):
        """Met à jour les couleurs dans le CSS."""
        css_path = Path(__file__).parent.parent / "templates" / "styles" / "document.css"
        
        if css_path.exists():
            try:
                content = css_path.read_text(encoding="utf-8")
                
                # Remplacer les couleurs
                primary = self.settings["colors"]["primary"]
                accent = self.settings["colors"]["accent"]
                
                # Simple remplacement des variables CSS
                import re
                content = re.sub(
                    r'--color-primary:\s*#[0-9a-fA-F]{6}',
                    f'--color-primary: {primary}',
                    content
                )
                content = re.sub(
                    r'--color-success:\s*#[0-9a-fA-F]{6}',
                    f'--color-success: {accent}',
                    content
                )
                
                css_path.write_text(content, encoding="utf-8")
                logger.info("Couleurs CSS mises à jour")
            except Exception as e:
                logger.error(f"Erreur mise à jour CSS: {e}")


def load_user_settings() -> dict:
    """Charge les paramètres utilisateur."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_company_info() -> dict:
    """Retourne les infos entreprise (fusion settings.py + user_settings.json)."""
    from config.settings import COMPANY_INFO
    
    user_settings = load_user_settings()
    if "company" in user_settings:
        # Fusionner avec priorité aux paramètres utilisateur
        merged = {**COMPANY_INFO, **user_settings["company"]}
        return merged
    
    return COMPANY_INFO
