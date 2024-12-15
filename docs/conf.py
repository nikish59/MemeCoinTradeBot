# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'MemeCoin_TradeBot'
copyright = '2024, Nikita'
author = 'Nikita'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys
sys.path.insert(0, os.path.abspath('../'))  # Путь на один уровень выше папки docs


extensions = [
    'sphinx.ext.autodoc',    # Для извлечения docstring из Python-кода
    'sphinx.ext.viewcode',   # Для отображения исходного кода
    'sphinx.ext.napoleon'    # Для поддержки Google и NumPy стилей docstring
]


templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
