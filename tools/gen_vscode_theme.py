#!/usr/bin/env python3
# ARES // gerador do tema de VS Code "ARES Cyber-Red"
# Mesma paleta do kitty/yazi/waybar: vermelho = estrutura, ciano = dados, fundo vermelho-preto.
# Escreve a extensão em home/.config/ares/vscode/ares-cyber-red/ (package.json + tema).
# Uso: python3 tools/gen_vscode_theme.py             -> só gera os arquivos
#      python3 tools/gen_vscode_theme.py --install   -> gera, empacota (.vsix) e instala no VS Code
# O VS Code só carrega extensões registradas, por isso o --install usa `code --install-extension`.
# Fundos 100% pretos (#000000) pra tela OLED: o que separa as áreas são as linhas vermelhas
# finas, e as cores (vermelho/ciano/rosa/menta/âmbar/azul) ficam no texto e nos destaques.

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EXT = os.path.join(ROOT, "home", ".config", "ares", "vscode", "ares-cyber-red")

# --- paleta ARES (a mesma do kitty.conf / yazi / waybar) --------------------------------------
BG = "#000000"        # fundo de tudo (preto puro: OLED apaga o pixel)
PANEL = "#000000"     # painéis, barra de título, abas inativas (também preto)
MODULE = "#120a0e"    # só hover/realce sutil (o resto fica preto)
LINE = "#3a1018"      # linhas e bordas
LINE2 = "#241016"     # borda mais discreta
RED = "#ff1f3d"
RED2 = "#ff5a6e"
RED_DIM = "#8f1426"
TEXT = "#e8e2e4"
MUTED = "#7a6f73"
DIM = "#4a3a40"
CYAN = "#00f0ff"
CYAN2 = "#7af8ff"
MINT = "#2bd9a0"
MINT2 = "#6ff2c4"
AMBER = "#ffb000"
AMBER2 = "#ffd166"
BLUE = "#2a7fff"
BLUE2 = "#6aa8ff"
MAGENTA = "#ff2a8a"
MAGENTA2 = "#ff70b3"
WHITE = "#ffffff"
COLD = "#000000"      # painel inferior / terminal


def a(color, alpha):
    """Cor #rrggbb + alfa (0-1) -> #rrggbbaa."""
    return f"{color}{round(alpha * 255):02x}"


# --- workbench ----------------------------------------------------------------------------------
colors = {
    # base
    "foreground": TEXT,
    "descriptionForeground": MUTED,
    "disabledForeground": DIM,
    "errorForeground": RED2,
    "focusBorder": a(CYAN, 0.6),
    "contrastBorder": "#00000000",
    "contrastActiveBorder": CYAN,
    "icon.foreground": TEXT,
    "selection.background": a(RED_DIM, 0.75),
    "widget.shadow": "#000000aa",
    "widget.border": LINE,
    "sash.hoverBorder": RED,
    "toolbar.hoverBackground": MODULE,
    "toolbar.activeBackground": LINE,
    "textLink.foreground": CYAN,
    "textLink.activeForeground": CYAN2,
    "textPreformat.foreground": MINT2,
    "textPreformat.background": BG,
    "textCodeBlock.background": BG,
    "textBlockQuote.background": PANEL,
    "textBlockQuote.border": RED,
    "textSeparator.foreground": LINE,

    # janela / barra de título
    "titleBar.activeBackground": PANEL,
    "titleBar.activeForeground": TEXT,
    "titleBar.inactiveBackground": BG,
    "titleBar.inactiveForeground": MUTED,
    "titleBar.border": LINE,
    "menubar.selectionBackground": RED,
    "menubar.selectionForeground": BG,
    "menubar.selectionBorder": RED,
    "menu.background": PANEL,
    "menu.foreground": TEXT,
    "menu.selectionBackground": RED,
    "menu.selectionForeground": BG,
    "menu.separatorBackground": LINE,
    "menu.border": LINE,
    "commandCenter.background": BG,
    "commandCenter.foreground": TEXT,
    "commandCenter.activeBackground": MODULE,
    "commandCenter.border": LINE,
    "commandCenter.activeBorder": RED,
    "commandCenter.debuggingBackground": a(AMBER, 0.25),

    # barra de atividades
    "activityBar.background": PANEL,
    "activityBar.foreground": WHITE,
    "activityBar.inactiveForeground": MUTED,
    "activityBar.border": LINE,
    "activityBar.activeBorder": RED,
    "activityBar.activeBackground": a(RED, 0.10),
    "activityBar.activeFocusBorder": CYAN,
    "activityBarBadge.background": CYAN,
    "activityBarBadge.foreground": BG,
    "activityBarTop.foreground": WHITE,
    "activityBarTop.inactiveForeground": MUTED,
    "activityBarTop.activeBorder": RED,
    "activityBarTop.activeBackground": a(RED, 0.10),
    "activityBarTop.background": PANEL,
    "activityBarTop.dropBorder": CYAN,
    "activityBarTop.border": LINE,
    "badge.background": CYAN,
    "badge.foreground": BG,

    # layout "flutuante" do VS Code 1.141: cards sobre um fundo (shell)
    "modernUI.shellBackground": PANEL,
    "modernUI.inactiveShellBackground": BG,
    "surface.background": BG,
    "surface.foreground": TEXT,
    "surface.border": LINE,
    "editor.border": LINE,
    "modernPanel.border": LINE,
    "modernSash.gripForeground": RED_DIM,
    "modernActivityBar.background": PANEL,
    "modernActivityBar.border": LINE,
    "modernActivityBar.activeBackground": a(RED, 0.14),
    "modernActivityBar.activeForeground": WHITE,
    "modernActivityBar.inactiveBackground": PANEL,
    "modernActivityBar.hoverBackground": MODULE,
    "modernActivityBar.hoverForeground": WHITE,
    "modernActivityBarItem.activeBackground": a(RED, 0.14),
    "modernActivityBarItem.activeForeground": WHITE,
    "modernActivityBarItem.hoverBackground": MODULE,
    "modernActivityBarItem.hoverForeground": WHITE,
    "modernEditorTab.activeBackground": BG,
    "modernEditorTab.activeForeground": WHITE,
    "modernEditorTab.activeHoverBackground": BG,
    "modernEditorTab.inactiveBackground": a(PANEL, 0.0),
    "modernEditorTab.hoverBackground": MODULE,
    "modernEditorTab.hoverForeground": WHITE,
    "modernEditorTab.activeActionBackground": a(RED, 0.18),
    "modernEditorTab.activeHoverActionBackground": a(RED, 0.30),
    "modernEditorTab.hoverActionBackground": a(RED, 0.18),
    "modernEditorTab.selectedActionBackground": a(RED, 0.18),
    "modernTab.activeBackground": BG,
    "modernTab.activeForeground": WHITE,
    "modernTab.hoverBackground": MODULE,
    "modernTab.hoverForeground": WHITE,

    # barra lateral
    "sideBar.background": BG,
    "sideBar.foreground": TEXT,
    "sideBar.border": LINE,
    "sideBar.dropBackground": a(CYAN, 0.15),
    "sideBarTitle.foreground": CYAN,
    "sideBarSectionHeader.background": BG,
    "sideBarSectionHeader.foreground": RED2,
    "sideBarSectionHeader.border": LINE,
    "sideBarActivityBarTop.border": LINE,
    "sideBarStickyScroll.background": BG,

    # listas / árvores
    "list.activeSelectionBackground": a(RED_DIM, 0.55),
    "list.activeSelectionForeground": WHITE,
    "list.activeSelectionIconForeground": WHITE,
    "list.inactiveSelectionBackground": a(RED_DIM, 0.28),
    "list.inactiveSelectionForeground": TEXT,
    "list.focusBackground": a(RED_DIM, 0.45),
    "list.focusForeground": WHITE,
    "list.focusOutline": a(CYAN, 0.7),
    "list.hoverBackground": MODULE,
    "list.hoverForeground": WHITE,
    "list.highlightForeground": CYAN,
    "list.focusHighlightForeground": CYAN2,
    "list.invalidItemForeground": RED2,
    "list.errorForeground": RED2,
    "list.warningForeground": AMBER,
    "list.dropBackground": a(CYAN, 0.15),
    "tree.indentGuidesStroke": LINE,
    "tree.inactiveIndentGuidesStroke": LINE2,

    # abas e grupos de editores
    "editorGroup.border": LINE,
    "editorGroup.dropBackground": a(CYAN, 0.12),
    "editorGroupHeader.tabsBackground": PANEL,
    "editorGroupHeader.tabsBorder": LINE,
    "editorGroupHeader.noTabsBackground": PANEL,
    "tab.activeBackground": BG,
    "tab.activeForeground": WHITE,
    "tab.inactiveBackground": PANEL,
    "tab.inactiveForeground": MUTED,
    "tab.unfocusedActiveBackground": BG,
    "tab.unfocusedActiveForeground": TEXT,
    "tab.unfocusedInactiveBackground": PANEL,
    "tab.unfocusedInactiveForeground": DIM,
    "tab.border": LINE,
    "tab.lastPinnedBorder": RED,
    "tab.activeBorder": CYAN,
    "tab.activeBorderTop": RED,
    "tab.unfocusedActiveBorder": a(CYAN, 0.4),
    "tab.unfocusedActiveBorderTop": RED_DIM,
    "tab.hoverBackground": MODULE,
    "tab.hoverForeground": WHITE,
    "tab.hoverBorder": a(RED, 0.6),
    "tab.unfocusedHoverBackground": MODULE,
    "tab.activeModifiedBorder": CYAN,
    "tab.inactiveModifiedBorder": a(CYAN, 0.5),
    "tab.unfocusedActiveModifiedBorder": a(CYAN, 0.4),
    "tab.unfocusedInactiveModifiedBorder": a(CYAN, 0.25),
    "breadcrumb.background": BG,
    "breadcrumb.foreground": MUTED,
    "breadcrumb.focusForeground": CYAN,
    "breadcrumb.activeSelectionForeground": WHITE,
    "breadcrumbPicker.background": PANEL,

    # editor
    "editor.background": BG,
    "editor.foreground": TEXT,
    "editorLineNumber.foreground": "#5a4a50",
    "editorLineNumber.activeForeground": CYAN,
    "editorLineNumber.dimmedForeground": LINE,
    "editorCursor.foreground": RED,
    "editorCursor.background": BG,
    "editor.lineHighlightBackground": a(RED, 0.07),
    "editor.lineHighlightBorder": "#00000000",
    "editor.selectionBackground": a(RED_DIM, 0.75),
    "editor.inactiveSelectionBackground": a(RED_DIM, 0.35),
    "editor.selectionHighlightBackground": a(CYAN, 0.14),
    "editor.selectionHighlightBorder": a(CYAN, 0.35),
    "editor.wordHighlightBackground": a(CYAN, 0.12),
    "editor.wordHighlightStrongBackground": a(RED, 0.20),
    "editor.wordHighlightTextBackground": a(CYAN, 0.10),
    "editor.findMatchBackground": a(CYAN, 0.38),
    "editor.findMatchBorder": CYAN,
    "editor.findMatchHighlightBackground": a(CYAN, 0.18),
    "editor.findRangeHighlightBackground": a(RED_DIM, 0.25),
    "editor.hoverHighlightBackground": a(CYAN, 0.14),
    "editor.rangeHighlightBackground": a(RED, 0.08),
    "editor.symbolHighlightBackground": a(CYAN, 0.18),
    "editor.foldBackground": a(RED_DIM, 0.18),
    "editor.foldPlaceholderForeground": CYAN,
    "editor.linkedEditingBackground": a(CYAN, 0.15),
    "editor.snippetTabstopHighlightBackground": a(CYAN, 0.18),
    "editor.snippetFinalTabstopHighlightBorder": CYAN,
    "editorLink.activeForeground": CYAN,
    "editorWhitespace.foreground": "#2a1a20",
    "editorIndentGuide.background1": "#1f0d12",
    "editorIndentGuide.activeBackground1": a(RED, 0.55),
    "editorRuler.foreground": LINE,
    "editorCodeLens.foreground": DIM,
    "editorInlayHint.foreground": a(CYAN2, 0.65),
    "editorInlayHint.background": a(CYAN, 0.08),
    "editorInlayHint.typeForeground": a(CYAN2, 0.65),
    "editorInlayHint.parameterForeground": a(MAGENTA2, 0.7),
    "editorBracketMatch.background": a(CYAN, 0.18),
    "editorBracketMatch.border": CYAN,
    "editorBracketHighlight.foreground1": RED,
    "editorBracketHighlight.foreground2": CYAN,
    "editorBracketHighlight.foreground3": AMBER,
    "editorBracketHighlight.foreground4": MAGENTA2,
    "editorBracketHighlight.foreground5": MINT2,
    "editorBracketHighlight.foreground6": BLUE2,
    "editorBracketHighlight.unexpectedBracket.foreground": WHITE,
    "editorBracketPairGuide.activeBackground1": a(RED, 0.7),
    "editorBracketPairGuide.activeBackground2": a(CYAN, 0.7),
    "editorBracketPairGuide.activeBackground3": a(AMBER, 0.7),
    "editorBracketPairGuide.activeBackground4": a(MAGENTA2, 0.7),
    "editorBracketPairGuide.activeBackground5": a(MINT2, 0.7),
    "editorBracketPairGuide.activeBackground6": a(BLUE2, 0.7),
    "editorBracketPairGuide.background1": a(RED, 0.18),
    "editorBracketPairGuide.background2": a(CYAN, 0.18),
    "editorBracketPairGuide.background3": a(AMBER, 0.18),
    "editorBracketPairGuide.background4": a(MAGENTA2, 0.18),
    "editorBracketPairGuide.background5": a(MINT2, 0.18),
    "editorBracketPairGuide.background6": a(BLUE2, 0.18),
    "editorUnnecessaryCode.opacity": "#000000aa",
    "editorGutter.background": BG,
    "editorGutter.modifiedBackground": CYAN,
    "editorGutter.addedBackground": MINT,
    "editorGutter.deletedBackground": RED,
    "editorGutter.foldingControlForeground": CYAN,
    "editorGutter.commentRangeForeground": DIM,
    "editorOverviewRuler.border": "#00000000",
    "editorOverviewRuler.modifiedForeground": a(CYAN, 0.8),
    "editorOverviewRuler.addedForeground": a(MINT, 0.8),
    "editorOverviewRuler.deletedForeground": a(RED, 0.8),
    "editorOverviewRuler.errorForeground": RED,
    "editorOverviewRuler.warningForeground": AMBER,
    "editorOverviewRuler.infoForeground": CYAN,
    "editorOverviewRuler.findMatchForeground": a(CYAN, 0.8),
    "editorOverviewRuler.selectionHighlightForeground": a(CYAN, 0.6),
    "editorOverviewRuler.wordHighlightForeground": a(CYAN, 0.5),
    "editorOverviewRuler.wordHighlightStrongForeground": a(RED, 0.6),
    "editorOverviewRuler.currentContentForeground": a(CYAN, 0.6),
    "editorOverviewRuler.incomingContentForeground": a(MINT, 0.6),
    "editorOverviewRuler.bracketMatchForeground": CYAN,
    "editorError.foreground": RED,
    "editorError.background": a(RED, 0.10),
    "editorWarning.foreground": AMBER,
    "editorInfo.foreground": CYAN,
    "editorHint.foreground": MINT2,
    "problemsErrorIcon.foreground": RED,
    "problemsWarningIcon.foreground": AMBER,
    "problemsInfoIcon.foreground": CYAN,

    # widgets do editor (busca, sugestões, hover)
    "editorWidget.background": PANEL,
    "editorWidget.foreground": TEXT,
    "editorWidget.border": a(RED, 0.5),
    "editorWidget.resizeBorder": CYAN,
    "editorSuggestWidget.background": PANEL,
    "editorSuggestWidget.border": a(RED, 0.5),
    "editorSuggestWidget.foreground": TEXT,
    "editorSuggestWidget.selectedForeground": WHITE,
    "editorSuggestWidget.selectedIconForeground": CYAN,
    "editorSuggestWidget.selectedBackground": a(RED_DIM, 0.55),
    "editorSuggestWidget.highlightForeground": CYAN,
    "editorSuggestWidget.focusHighlightForeground": CYAN2,
    "editorSuggestWidgetStatus.foreground": MUTED,
    "editorHoverWidget.background": PANEL,
    "editorHoverWidget.foreground": TEXT,
    "editorHoverWidget.border": a(RED, 0.5),
    "editorHoverWidget.highlightForeground": CYAN,
    "editorHoverWidget.statusBarBackground": BG,
    "editorStickyScroll.background": BG,
    "editorStickyScrollHover.background": MODULE,
    "editorStickyScroll.border": LINE,
    "editorGhostText.foreground": a(CYAN2, 0.4),
    "editorMarkerNavigation.background": PANEL,
    "editorMarkerNavigationError.background": RED,
    "editorMarkerNavigationWarning.background": AMBER,
    "editorMarkerNavigationInfo.background": CYAN,
    "peekView.border": RED,
    "peekViewEditor.background": BG,
    "peekViewEditor.matchHighlightBackground": a(CYAN, 0.3),
    "peekViewEditorGutter.background": BG,
    "peekViewResult.background": PANEL,
    "peekViewResult.fileForeground": WHITE,
    "peekViewResult.lineForeground": MUTED,
    "peekViewResult.matchHighlightBackground": a(CYAN, 0.3),
    "peekViewResult.selectionBackground": a(RED_DIM, 0.55),
    "peekViewResult.selectionForeground": WHITE,
    "peekViewTitle.background": BG,
    "peekViewTitleLabel.foreground": CYAN,
    "peekViewTitleDescription.foreground": MUTED,

    # diff / merge
    "diffEditor.insertedTextBackground": a(MINT, 0.18),
    "diffEditor.removedTextBackground": a(RED, 0.22),
    "diffEditor.insertedLineBackground": a(MINT, 0.10),
    "diffEditor.removedLineBackground": a(RED, 0.12),
    "diffEditor.diagonalFill": LINE,
    "diffEditorGutter.insertedLineBackground": a(MINT, 0.20),
    "diffEditorGutter.removedLineBackground": a(RED, 0.25),
    "diffEditor.move.border": CYAN,
    "diffEditor.moveActive.border": RED,
    "merge.currentHeaderBackground": a(CYAN, 0.35),
    "merge.currentContentBackground": a(CYAN, 0.12),
    "merge.incomingHeaderBackground": a(MINT, 0.35),
    "merge.incomingContentBackground": a(MINT, 0.12),
    "merge.commonHeaderBackground": a(MUTED, 0.35),
    "merge.commonContentBackground": a(MUTED, 0.12),
    "merge.border": LINE,
    "mergeEditor.change.background": a(RED, 0.12),
    "mergeEditor.change.word.background": a(RED, 0.25),
    "mergeEditor.conflict.unhandledUnfocused.border": a(MAGENTA, 0.5),
    "mergeEditor.conflict.unhandledFocused.border": MAGENTA,
    "mergeEditor.conflict.handledUnfocused.border": a(MINT, 0.4),
    "mergeEditor.conflict.handledFocused.border": MINT,

    # entradas, botões, dropdowns
    "input.background": PANEL,
    "input.foreground": TEXT,
    "input.border": LINE,
    "input.placeholderForeground": DIM,
    "inputOption.activeBackground": a(CYAN, 0.22),
    "inputOption.activeBorder": CYAN,
    "inputOption.activeForeground": CYAN2,
    "inputOption.hoverBackground": a(RED, 0.2),
    "inputValidation.errorBackground": a(RED, 0.15),
    "inputValidation.errorBorder": RED,
    "inputValidation.errorForeground": TEXT,
    "inputValidation.warningBackground": a(AMBER, 0.12),
    "inputValidation.warningBorder": AMBER,
    "inputValidation.infoBackground": a(CYAN, 0.12),
    "inputValidation.infoBorder": CYAN,
    "button.background": RED,
    "button.foreground": BG,
    "button.hoverBackground": RED2,
    "button.border": RED,
    "button.separator": a(BG, 0.4),
    "button.secondaryBackground": BG,
    "button.secondaryForeground": TEXT,
    "button.secondaryHoverBackground": LINE,
    "checkbox.background": PANEL,
    "checkbox.foreground": CYAN,
    "checkbox.border": LINE,
    "checkbox.selectBackground": PANEL,
    "dropdown.background": PANEL,
    "dropdown.foreground": TEXT,
    "dropdown.border": LINE,
    "dropdown.listBackground": PANEL,
    "keybindingLabel.background": BG,
    "keybindingLabel.foreground": CYAN2,
    "keybindingLabel.border": LINE,
    "keybindingLabel.bottomBorder": RED_DIM,
    "progressBar.background": RED,
    "scrollbar.shadow": "#00000000",
    "scrollbarSlider.background": a(RED_DIM, 0.35),
    "scrollbarSlider.hoverBackground": a(RED, 0.5),
    "scrollbarSlider.activeBackground": a(CYAN, 0.55),
    "minimap.background": BG,
    "minimap.selectionHighlight": a(CYAN, 0.6),
    "minimap.findMatchHighlight": CYAN,
    "minimap.errorHighlight": RED,
    "minimap.warningHighlight": AMBER,
    "minimap.selectionOccurrenceHighlight": a(CYAN, 0.4),
    "minimapSlider.background": a(CYAN, 0.10),
    "minimapSlider.hoverBackground": a(CYAN, 0.20),
    "minimapSlider.activeBackground": a(CYAN, 0.30),
    "minimapGutter.addedBackground": MINT,
    "minimapGutter.modifiedBackground": CYAN,
    "minimapGutter.deletedBackground": RED,

    # painel inferior / terminal
    "panel.background": COLD,
    "panel.border": LINE,
    "panel.dropBorder": CYAN,
    "panelTitle.activeForeground": WHITE,
    "panelTitle.inactiveForeground": MUTED,
    "panelTitle.activeBorder": RED,
    "panelTitleBadge.background": CYAN,
    "panelTitleBadge.foreground": BG,
    "panelSection.border": LINE,
    "panelSectionHeader.background": BG,
    "panelStickyScroll.background": COLD,
    "outputView.background": COLD,
    "terminal.background": COLD,
    "terminal.foreground": TEXT,
    "terminal.selectionBackground": a(RED_DIM, 0.75),
    "terminal.selectionForeground": WHITE,
    "terminal.inactiveSelectionBackground": a(RED_DIM, 0.35),
    "terminal.findMatchBackground": a(CYAN, 0.38),
    "terminal.findMatchBorder": CYAN,
    "terminal.findMatchHighlightBackground": a(CYAN, 0.18),
    "terminal.border": LINE,
    "terminal.tab.activeBorder": RED,
    "terminalCursor.foreground": RED,
    "terminalCursor.background": BG,
    "terminalCommandDecoration.defaultBackground": DIM,
    "terminalCommandDecoration.successBackground": MINT,
    "terminalCommandDecoration.errorBackground": RED,
    "terminalOverviewRuler.cursorForeground": a(RED, 0.7),
    "terminalOverviewRuler.findMatchForeground": CYAN,
    "terminal.ansiBlack": "#1a0f14",
    "terminal.ansiRed": "#ff1f3d",
    "terminal.ansiGreen": "#2bd9a0",
    "terminal.ansiYellow": "#ffb000",
    "terminal.ansiBlue": "#2a7fff",
    "terminal.ansiMagenta": "#ff2a8a",
    "terminal.ansiCyan": "#00f0ff",
    "terminal.ansiWhite": "#c9c0c4",
    "terminal.ansiBrightBlack": "#4a3a40",
    "terminal.ansiBrightRed": "#ff5a6e",
    "terminal.ansiBrightGreen": "#6ff2c4",
    "terminal.ansiBrightYellow": "#ffd166",
    "terminal.ansiBrightBlue": "#6aa8ff",
    "terminal.ansiBrightMagenta": "#ff70b3",
    "terminal.ansiBrightCyan": "#7af8ff",
    "terminal.ansiBrightWhite": "#ffffff",

    # barra de status: escura, com o vermelho/ciano só nos indicadores
    "statusBar.background": PANEL,
    "statusBar.foreground": TEXT,
    "statusBar.border": RED_DIM,
    "statusBar.debuggingBackground": AMBER,
    "statusBar.debuggingForeground": BG,
    "statusBar.debuggingBorder": AMBER,
    "statusBar.noFolderBackground": BG,
    "statusBar.noFolderForeground": TEXT,
    "statusBar.noFolderBorder": RED_DIM,
    "statusBarItem.hoverBackground": LINE,
    "statusBarItem.hoverForeground": WHITE,
    "statusBarItem.activeBackground": RED_DIM,
    "statusBarItem.remoteBackground": RED,
    "statusBarItem.remoteForeground": BG,
    "statusBarItem.remoteHoverBackground": RED2,
    "statusBarItem.prominentBackground": a(CYAN, 0.25),
    "statusBarItem.prominentForeground": CYAN2,
    "statusBarItem.prominentHoverBackground": a(CYAN, 0.4),
    "statusBarItem.errorBackground": RED,
    "statusBarItem.errorForeground": BG,
    "statusBarItem.warningBackground": AMBER,
    "statusBarItem.warningForeground": BG,
    "statusBarItem.compactHoverBackground": LINE,
    "statusBarItem.focusBorder": CYAN,
    "statusBar.focusBorder": CYAN,

    # notificações, paleta de comandos, popups
    "notifications.background": PANEL,
    "notifications.foreground": TEXT,
    "notifications.border": RED,
    "notificationCenter.border": RED,
    "notificationCenterHeader.background": BG,
    "notificationCenterHeader.foreground": CYAN,
    "notificationToast.border": RED,
    "notificationLink.foreground": CYAN,
    "notificationsErrorIcon.foreground": RED,
    "notificationsWarningIcon.foreground": AMBER,
    "notificationsInfoIcon.foreground": CYAN,
    "quickInput.background": PANEL,
    "quickInput.foreground": TEXT,
    "quickInputTitle.background": BG,
    "quickInputList.focusBackground": a(RED_DIM, 0.55),
    "quickInputList.focusForeground": WHITE,
    "quickInputList.focusIconForeground": CYAN,
    "pickerGroup.foreground": CYAN,
    "pickerGroup.border": LINE,
    "banner.background": BG,
    "banner.foreground": TEXT,
    "banner.iconForeground": CYAN,

    # gráficos / ícones de símbolos / git
    "gitDecoration.addedResourceForeground": MINT,
    "gitDecoration.modifiedResourceForeground": CYAN,
    "gitDecoration.deletedResourceForeground": RED,
    "gitDecoration.renamedResourceForeground": BLUE2,
    "gitDecoration.stageModifiedResourceForeground": CYAN2,
    "gitDecoration.stageDeletedResourceForeground": RED2,
    "gitDecoration.untrackedResourceForeground": MINT2,
    "gitDecoration.ignoredResourceForeground": DIM,
    "gitDecoration.conflictingResourceForeground": MAGENTA,
    "gitDecoration.submoduleResourceForeground": AMBER,
    "scmGraph.historyItemHoverDefaultLabelForeground": BG,
    "scmGraph.foreground1": RED,
    "scmGraph.foreground2": CYAN,
    "scmGraph.foreground3": AMBER,
    "scmGraph.foreground4": MAGENTA2,
    "scmGraph.foreground5": MINT2,
    "charts.foreground": TEXT,
    "charts.lines": MUTED,
    "charts.red": RED,
    "charts.blue": BLUE2,
    "charts.yellow": AMBER,
    "charts.orange": AMBER2,
    "charts.green": MINT,
    "charts.purple": MAGENTA2,
    "symbolIcon.functionForeground": CYAN,
    "symbolIcon.methodForeground": CYAN,
    "symbolIcon.constructorForeground": CYAN2,
    "symbolIcon.classForeground": AMBER2,
    "symbolIcon.interfaceForeground": AMBER2,
    "symbolIcon.structForeground": AMBER2,
    "symbolIcon.enumeratorForeground": AMBER,
    "symbolIcon.enumeratorMemberForeground": AMBER,
    "symbolIcon.constantForeground": AMBER,
    "symbolIcon.variableForeground": TEXT,
    "symbolIcon.fieldForeground": CYAN2,
    "symbolIcon.propertyForeground": CYAN2,
    "symbolIcon.keywordForeground": RED,
    "symbolIcon.moduleForeground": BLUE2,
    "symbolIcon.namespaceForeground": BLUE2,
    "symbolIcon.packageForeground": BLUE2,
    "symbolIcon.stringForeground": MINT2,
    "symbolIcon.numberForeground": AMBER,
    "symbolIcon.booleanForeground": MAGENTA2,
    "symbolIcon.operatorForeground": RED2,
    "symbolIcon.eventForeground": MAGENTA2,
    "symbolIcon.typeParameterForeground": AMBER2,
    "symbolIcon.snippetForeground": MINT2,
    "symbolIcon.textForeground": TEXT,

    # depuração
    "debugToolBar.background": BG,
    "debugToolBar.border": RED,
    "debugIcon.breakpointForeground": RED,
    "debugIcon.breakpointDisabledForeground": DIM,
    "debugIcon.breakpointUnverifiedForeground": RED_DIM,
    "debugIcon.startForeground": MINT,
    "debugIcon.pauseForeground": AMBER,
    "debugIcon.stopForeground": RED,
    "debugIcon.disconnectForeground": RED,
    "debugIcon.restartForeground": MINT,
    "debugIcon.stepOverForeground": CYAN,
    "debugIcon.stepIntoForeground": CYAN,
    "debugIcon.stepOutForeground": CYAN,
    "debugIcon.continueForeground": MINT,
    "debugIcon.stepBackForeground": CYAN,
    "debugConsole.errorForeground": RED2,
    "debugConsole.warningForeground": AMBER,
    "debugConsole.infoForeground": CYAN,
    "debugConsole.sourceForeground": MUTED,
    "debugConsoleInputIcon.foreground": CYAN,
    "debugTokenExpression.name": CYAN2,
    "debugTokenExpression.value": MINT2,
    "debugTokenExpression.string": MINT2,
    "debugTokenExpression.number": AMBER,
    "debugTokenExpression.boolean": MAGENTA2,
    "debugTokenExpression.error": RED2,
    "editor.stackFrameHighlightBackground": a(AMBER, 0.18),
    "editor.focusedStackFrameHighlightBackground": a(MINT, 0.20),

    # configurações, extensões, welcome
    "settings.headerForeground": RED,
    "settings.modifiedItemIndicator": CYAN,
    "settings.dropdownBackground": PANEL,
    "settings.dropdownBorder": LINE,
    "settings.textInputBackground": PANEL,
    "settings.textInputBorder": LINE,
    "settings.numberInputBackground": PANEL,
    "settings.numberInputBorder": LINE,
    "settings.checkboxBackground": PANEL,
    "settings.checkboxBorder": LINE,
    "settings.focusedRowBackground": a(RED, 0.06),
    "settings.focusedRowBorder": a(CYAN, 0.5),
    "settings.rowHoverBackground": a(RED, 0.04),
    "extensionButton.prominentBackground": RED,
    "extensionButton.prominentForeground": BG,
    "extensionButton.prominentHoverBackground": RED2,
    "extensionButton.separator": a(BG, 0.4),
    "extensionBadge.remoteBackground": RED,
    "extensionBadge.remoteForeground": BG,
    "extensionIcon.starForeground": AMBER,
    "extensionIcon.verifiedForeground": CYAN,
    "extensionIcon.preReleaseForeground": MAGENTA2,
    "extensionIcon.sponsorForeground": MAGENTA2,
    "welcomePage.background": BG,
    "welcomePage.tileBackground": PANEL,
    "welcomePage.tileHoverBackground": MODULE,
    "welcomePage.tileBorder": LINE,
    "welcomePage.progress.background": PANEL,
    "welcomePage.progress.foreground": CYAN,
    "walkThrough.embeddedEditorBackground": PANEL,
    "walkthrough.stepTitle.foreground": CYAN,
    "interactive.activeCodeBorder": RED,
    "interactive.inactiveCodeBorder": LINE,
    "notebook.cellBorderColor": LINE,
    "notebook.focusedCellBorder": CYAN,
    "notebook.cellEditorBackground": PANEL,
    "notebook.selectedCellBackground": a(RED, 0.06),
    "notebook.cellToolbarSeparator": LINE,
    "testing.iconPassed": MINT,
    "testing.iconFailed": RED,
    "testing.iconErrored": RED2,
    "testing.iconQueued": AMBER,
    "testing.iconUnset": MUTED,
    "testing.iconSkipped": MUTED,
    "testing.runAction": MINT,
    "testing.message.error.lineBackground": a(RED, 0.12),
    "keybindingTable.headerBackground": BG,
    "keybindingTable.rowsBackground": a(RED, 0.04),
    "editorLightBulb.foreground": AMBER,
    "editorLightBulbAutoFix.foreground": CYAN,
    "editorLightBulbAi.foreground": MAGENTA2,
    "chat.requestBorder": LINE,
    "chat.requestBackground": PANEL,
    "chat.slashCommandBackground": a(RED, 0.2),
    "chat.slashCommandForeground": RED2,
    "chat.avatarBackground": MODULE,
    "chat.avatarForeground": CYAN,
    "chat.linesAddedForeground": MINT,
    "chat.linesRemovedForeground": RED2,
}

# --- sintaxe (TextMate) -------------------------------------------------------------------------
# Papéis: vermelho = declarações · ciano = funções · ciano claro = propriedades/chaves ·
#         âmbar = números/constantes e tipos · menta = strings · rosa = fluxo/decorators ·
#         azul = módulos/primitivos · branco = variáveis · cinza quente = comentários
tokens = [
    ("comment, punctuation.definition.comment", MUTED, "italic"),
    ("comment.block.documentation, comment.block.javadoc, string.quoted.docstring", "#9a8c92", "italic"),
    ("comment keyword.codetag.notation, comment.line.todo", AMBER, "bold italic"),

    ("string, string.quoted, string.template, punctuation.definition.string", MINT2, None),
    ("string.regexp, constant.other.character-class.regexp, string.regexp keyword.operator", MAGENTA2, None),
    ("constant.character.escape, constant.other.placeholder, string.template meta.template.expression, punctuation.definition.template-expression", CYAN, None),
    ("constant.numeric, constant.numeric.decimal, constant.numeric.hex, keyword.other.unit", AMBER, None),
    ("constant.language, constant.language.boolean, constant.language.null, constant.language.undefined, constant.language.nil, support.constant.builtin", MAGENTA2, None),
    ("constant, constant.other, variable.other.constant, variable.other.enummember, entity.name.constant", AMBER2, None),
    ("support.constant", AMBER, None),

    ("storage.type, storage.modifier, keyword.declaration, keyword.other.def, keyword.other.fn, keyword.other.class, keyword.other.function, keyword.other.local, keyword.other.let, keyword.other.var, keyword.other.const, keyword.other.struct, keyword.other.enum", RED, None),
    ("keyword, keyword.other, keyword.operator.new, keyword.operator.expression, keyword.operator.logical.python, keyword.operator.wordlike", RED, None),
    ("keyword.control, keyword.control.flow, keyword.control.import, keyword.control.from, keyword.control.export, keyword.control.conditional, keyword.control.loop, keyword.control.return, keyword.control.trycatch, keyword.control.exception", "#ff4f7b", None),
    ("keyword.operator, keyword.operator.assignment, keyword.operator.arithmetic, keyword.operator.comparison, keyword.operator.logical, keyword.operator.relational, keyword.operator.type, punctuation.separator.key-value", RED2, None),

    ("variable, variable.other, variable.other.readwrite, meta.definition.variable, string.interpolated variable", TEXT, None),
    ("variable.parameter, meta.function.parameters variable, meta.parameters variable, variable.parameter.function", "#ffb3bd", None),
    ("variable.language, variable.language.this, variable.language.self, variable.language.super, entity.name.tag.this", RED2, "italic"),
    ("variable.other.property, variable.other.object.property, meta.object-literal.key, support.variable.property, variable.other.member", CYAN2, None),
    ("support.type.property-name, support.type.property-name.json, meta.structure.dictionary.key string.quoted.double", CYAN2, None),

    ("entity.name.function, support.function, meta.function-call entity.name.function, meta.function-call.generic, support.function.builtin", CYAN, None),
    ("meta.function-call.python, meta.method-call, entity.name.function.member", CYAN, None),
    ("entity.name.function.decorator, meta.decorator, meta.annotation, storage.type.annotation, punctuation.definition.decorator, punctuation.decorator, entity.name.function.macro, support.function.magic", MAGENTA2, "italic"),
    ("entity.name.type, entity.name.class, entity.name.type.class, entity.name.struct, entity.name.enum, entity.name.interface, entity.other.inherited-class, support.class, support.type.exception", AMBER2, None),
    ("support.type, support.type.builtin, support.type.primitive, storage.type.primitive, storage.type.built-in, keyword.type, entity.name.type.primitive, support.type.python", BLUE2, None),
    ("entity.name.namespace, entity.name.module, entity.name.type.module, support.module, entity.name.import, meta.import variable.other.readwrite.alias", BLUE2, None),
    ("entity.name.label, entity.name.section, entity.other.attribute-name.pseudo-element", MAGENTA2, None),

    ("punctuation, meta.brace, punctuation.separator, punctuation.terminator, punctuation.accessor, meta.delimiter", "#9a8a90", None),
    ("punctuation.definition.parameters, punctuation.definition.arguments, punctuation.section.embedded, punctuation.definition.block", "#b9a9af", None),
    ("invalid, invalid.illegal", WHITE, None),
    ("invalid.deprecated", AMBER, "strikethrough"),

    # HTML / XML
    ("entity.name.tag, meta.tag entity.name.tag, entity.name.tag.html, entity.name.tag.xml", RED, None),
    ("punctuation.definition.tag, meta.tag.sgml.doctype, meta.tag.preprocessor", "#c04a5e", None),
    ("entity.other.attribute-name, entity.other.attribute-name.html", AMBER2, None),
    ("meta.tag string.quoted, meta.attribute string", MINT2, None),
    ("entity.name.tag.custom, support.class.component", AMBER2, None),

    # CSS / SCSS
    ("entity.name.tag.css, entity.name.tag.scss, entity.other.attribute-name.parent-selector.css", RED, None),
    ("entity.other.attribute-name.class.css, entity.other.attribute-name.class.scss, entity.other.attribute-name.class", AMBER2, None),
    ("entity.other.attribute-name.id.css, entity.other.attribute-name.id", MAGENTA2, None),
    ("support.type.property-name.css, support.type.property-name.scss, meta.property-name.css", CYAN2, None),
    ("support.constant.property-value.css, support.constant.color, constant.other.color, support.constant.font-name, meta.property-value.css constant", MINT2, None),
    ("variable.css, variable.argument.css, variable.scss, variable.other.less, support.type.custom-property.name", "#ff8a9a", None),
    ("keyword.control.at-rule, keyword.control.at-rule.media, punctuation.definition.keyword.css", MAGENTA2, None),
    ("support.function.misc.css, support.function.transform.css, support.function.gradient.css", CYAN, None),

    # JSON
    ("source.json support.type.property-name, source.json meta.structure.dictionary.json support.type.property-name.json", CYAN2, None),
    ("source.json meta.structure.dictionary.value.json string.quoted.double.json", MINT2, None),

    # Markdown
    ("markup.heading, markup.heading entity.name, entity.name.section.markdown, punctuation.definition.heading.markdown", RED, "bold"),
    ("markup.heading.setext", RED, "bold"),
    ("markup.bold, markup.bold string", WHITE, "bold"),
    ("markup.italic", CYAN2, "italic"),
    ("markup.strikethrough", MUTED, "strikethrough"),
    ("markup.inline.raw, markup.fenced_code.block, markup.raw.block.markdown, fenced_code.block.language", MINT2, None),
    ("markup.underline.link, string.other.link, markup.underline.link.image.markdown", CYAN, None),
    ("string.other.link.title.markdown, string.other.link.description.markdown, constant.other.reference.link.markdown", CYAN2, None),
    ("punctuation.definition.list.begin.markdown, markup.list.numbered.bullet, beginning.punctuation.definition.list.markdown", RED, None),
    ("markup.quote, markup.quote punctuation.definition.quote.begin", "#b9a9af", "italic"),
    ("meta.separator.markdown, punctuation.definition.thematic-break", LINE, None),
    ("punctuation.definition.bold.markdown, punctuation.definition.italic.markdown, punctuation.definition.raw.markdown, punctuation.definition.markdown, punctuation.definition.string.begin.markdown, punctuation.definition.string.end.markdown, punctuation.definition.metadata.markdown", RED_DIM, None),

    # shell
    ("support.function.builtin.shell, support.function.builtin.bash, support.function.shell", CYAN, None),
    ("variable.other.normal.shell, variable.other.positional.shell, variable.other.bracket.shell, variable.other.special.shell, punctuation.definition.variable.shell", AMBER2, None),
    ("keyword.operator.redirect.shell, keyword.operator.pipe.shell, keyword.operator.list.shell, keyword.operator.logical.shell", RED2, None),
    ("meta.function-call.arguments.shell, string.unquoted.argument.shell, constant.other.option.shell, constant.other.option.dash.shell", "#d4c8cc", None),

    # Python / Lua / TOML / INI / YAML
    ("support.function.builtin.python, support.type.python, meta.function-call.generic.python", CYAN, None),
    ("variable.parameter.function.language.special.self.python, variable.language.special.self.python, variable.parameter.function.language.special.cls.python", RED2, "italic"),
    ("support.function.builtin.lua, support.function.library.lua, support.function.any-method.lua", CYAN, None),
    ("entity.name.table.toml, support.type.property-name.table.toml, entity.name.section.group-title.ini, entity.other.attribute-name.table.toml", RED, None),
    ("support.type.property-name.toml, support.type.property-name.yaml, entity.name.tag.yaml, keyword.other.definition.ini, support.type.property-name.array.toml", CYAN2, None),
    ("punctuation.definition.anchor.yaml, punctuation.definition.alias.yaml, entity.name.type.anchor.yaml, variable.other.alias.yaml", MAGENTA2, None),

    # diff
    ("markup.inserted, meta.diff.header.to-file, punctuation.definition.inserted", MINT2, None),
    ("markup.deleted, meta.diff.header.from-file, punctuation.definition.deleted", RED2, None),
    ("markup.changed, punctuation.definition.changed", CYAN, None),
    ("meta.diff.range, meta.diff.header, meta.separator.diff", MAGENTA2, None),
]

# --- tokens semânticos (LSP: pylance, tsserver, rust-analyzer, lua-ls...) -----------------------
semantic = {
    "namespace": BLUE2,
    "class": AMBER2,
    "enum": AMBER2,
    "interface": AMBER2,
    "struct": AMBER2,
    "type": AMBER2,
    "typeParameter": AMBER2,
    "builtinType": BLUE2,
    "function": CYAN,
    "method": CYAN,
    "member": CYAN,
    "macro": MAGENTA2,
    "decorator": {"foreground": MAGENTA2, "italic": True},
    "variable": TEXT,
    "variable.readonly": AMBER2,
    "variable.defaultLibrary": BLUE2,
    "parameter": "#ffb3bd",
    "property": CYAN2,
    "enumMember": AMBER,
    "event": MAGENTA2,
    "keyword": RED,
    "string": MINT2,
    "number": AMBER,
    "regexp": MAGENTA2,
    "operator": RED2,
    "selfParameter": {"foreground": RED2, "italic": True},
    "clsParameter": {"foreground": RED2, "italic": True},
    "*.deprecated": {"strikethrough": True},
}


def build_theme():
    theme = {
        "$schema": "vscode://schemas/color-theme",
        "name": "ARES Cyber-Red",
        "type": "dark",
        "semanticHighlighting": True,
        "colors": colors,
        "tokenColors": [],
        "semanticTokenColors": semantic,
    }
    for scopes, color, style in tokens:
        settings = {"foreground": color}
        if style:
            settings["fontStyle"] = style
        theme["tokenColors"].append({"scope": [s.strip() for s in scopes.split(",")], "settings": settings})
    return theme


PACKAGE = {
    "name": "ares-cyber-red",
    "displayName": "ARES Cyber-Red",
    "description": "Tema ARES MAINFRAME: vermelho (estrutura) + ciano (dados) sobre vermelho-preto, igual ao resto do sistema.",
    "version": "1.0.0",
    "publisher": "ares",
    "license": "MIT",
    "engines": {"vscode": "^1.80.0"},
    "categories": ["Themes"],
    "contributes": {
        "themes": [
            {
                "label": "ARES Cyber-Red",
                "uiTheme": "vs-dark",
                "path": "./themes/ares-cyber-red-color-theme.json",
            }
        ]
    },
}

VSIX_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}" />
    <DisplayName>{displayName}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code" /></Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
"""

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/Content-Types">
  <Default Extension=".json" ContentType="application/json" />
  <Default Extension=".vsixmanifest" ContentType="text/xml" />
</Types>
"""


def write_extension():
    os.makedirs(os.path.join(EXT, "themes"), exist_ok=True)
    with open(os.path.join(EXT, "package.json"), "w") as f:
        json.dump(PACKAGE, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(os.path.join(EXT, "themes", "ares-cyber-red-color-theme.json"), "w") as f:
        json.dump(build_theme(), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"tema escrito em {os.path.relpath(EXT, ROOT)} ({len(colors)} cores, {len(tokens)} regras de sintaxe)")


def build_vsix(path):
    """Um .vsix é um zip com o manifesto + a pasta extension/."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("extension.vsixmanifest", VSIX_MANIFEST.format(**PACKAGE))
        for folder, _, files in os.walk(EXT):
            for name in files:
                full = os.path.join(folder, name)
                z.write(full, os.path.join("extension", os.path.relpath(full, EXT)))


def install(code, extra):
    code = code or shutil.which("code")
    if not code:
        raise SystemExit("`code` não encontrado no PATH (use --code /caminho/do/code)")
    with tempfile.TemporaryDirectory() as tmp:
        vsix = os.path.join(tmp, "ares-cyber-red.vsix")
        build_vsix(vsix)
        subprocess.run([code, *extra, "--install-extension", vsix, "--force"], check=True)


def main():
    ap = argparse.ArgumentParser(description="Gera (e opcionalmente instala) o tema ARES Cyber-Red do VS Code")
    ap.add_argument("--install", action="store_true", help="empacota e instala no VS Code")
    ap.add_argument("--code", help="binário do VS Code (padrão: o `code` do PATH)")
    ap.add_argument("--extensions-dir", help="pasta de extensões alternativa (testes)")
    ap.add_argument("--user-data-dir", help="pasta de dados alternativa (testes)")
    args = ap.parse_args()
    write_extension()
    if args.install:
        extra = []
        if args.extensions_dir:
            extra += ["--extensions-dir", args.extensions_dir]
        if args.user_data_dir:
            extra += ["--user-data-dir", args.user_data_dir]
        install(args.code, extra)


if __name__ == "__main__":
    main()
