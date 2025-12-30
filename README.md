# GEN-DOC 📄

Système de génération automatisée de documents professionnels (Factures, Bulletins de salaire) au format PDF.

## ✨ Fonctionnalités

- 📊 **Import CSV/Excel** avec détection automatique d'encodage
- 📄 **Templates professionnels** optimisés A4
- 💳 **QR Code EPC** pour paiement SEPA instantané
- 📁 **Export comptable** Sage/Cegid/FEC
- 🗂️ **Archivage légal** avec hash SHA256
- 🖥️ **Interface graphique** moderne (CustomTkinter)

## 🚀 Installation

```bash
# Cloner le projet
git clone https://github.com/votre-username/gendoc.git
cd gendoc

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

## 📖 Utilisation

### Interface graphique
```bash
./gendoc.sh
```

### Ligne de commande
```bash
# Factures
python main.py facture fichier.csv

# Bulletins de salaire
python main.py paie fichier.csv --period "Décembre 2024"
```

## ⚙️ Configuration

Modifiez `config/settings.py` pour personnaliser :
- Informations de l'entreprise
- IBAN/BIC (pour QR Code)
- Taux de TVA
- Cotisations sociales

## 📁 Structure

```
gendoc/
├── main.py              # Point d'entrée CLI
├── gendoc.sh            # Lanceur GUI
├── config/              # Configuration
├── core/                # Moteur de traitement
├── gui/                 # Interface graphique
├── templates/           # Templates HTML/CSS
├── database/            # Logs SQLite
└── output/              # PDF générés
```

## 📝 Licence

MIT License
