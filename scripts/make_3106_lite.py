#!/usr/bin/env python3
"""Create the 3106 Lite distribution from a pinned upstream source checkout.

The script does not change the original repository. It hides nonessential UI
routes and disables all in-app update requests, including manual checks.
"""
from __future__ import annotations

from pathlib import Path
import sys


def replace_exact(text: str, old: str, new: str, where: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{where}: expected one match, found {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


def cut_between(text: str, start: str, end: str, where: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise RuntimeError(f"{where}: cannot locate unique boundaries")
    a, b = text.index(start), text.index(end)
    if a >= b:
        raise RuntimeError(f"{where}: invalid boundary order")
    return text[:a] + text[b:]


def matching_brace(text: str, brace_start: int) -> int:
    """Return the index immediately after a Swift block's closing brace.

    Used only with known upstream sources and anchored signatures. A light
    lexer skips string literals and line/block comments.
    """
    depth = 0
    in_string = False
    block_comment = 0
    line_comment = False
    i = brace_start
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        if line_comment:
            if c == '\n':
                line_comment = False
            i += 1
            continue
        if block_comment:
            if c == '/' and n == '*':
                block_comment += 1
                i += 2
                continue
            if c == '*' and n == '/':
                block_comment -= 1
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '/' and n == '/':
            line_comment = True
            i += 2
            continue
        if c == '/' and n == '*':
            block_comment = 1
            i += 2
            continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == '{':
            depth += 1
        if c == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise RuntimeError('Unbalanced Swift block')


def strip_block(text: str, marker: str, where: str) -> str:
    if text.count(marker) != 1:
        raise RuntimeError(f"{where}: marker missing or ambiguous: {marker!r}")
    begin = text.index(marker)
    open_brace = text.index('{', begin + len(marker) - 1)
    finish = matching_brace(text, open_brace)
    # Strip one trailing newline; retain surrounding modifier chain layout.
    if finish < len(text) and text[finish] == '\n':
        finish += 1
    return text[:begin] + text[finish:]


def replace_block(text: str, marker: str, replacement: str, where: str) -> str:
    if text.count(marker) != 1:
        raise RuntimeError(f"{where}: marker missing or ambiguous: {marker!r}")
    begin = text.index(marker)
    open_brace = text.index('{', begin + len(marker) - 1)
    finish = matching_brace(text, open_brace)
    return text[:begin] + replacement + text[finish:]


FEATURE_HUB = '''import SwiftUI

/// Minimal home page. Advanced modules stay out of the Lite navigation.
struct FeatureHubView: View {
    @Environment(\.appLanguage) private var language
    let onSelectTab: (AppSection) -> Void
    let onOpenSettings: () -> Void
    let onOpenLogs: () -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    LabeledContent(language.text("home.version"), value: appVersion)
                    LabeledContent(language.text("home.backend"), value: SandboxAccess.backend.displayName)
                    if SandboxAccess.needsWorseQuery {
                        LabeledContent(language.text("home.app_group"), value: appGroupText)
                        if SandboxAccess.appGroup == nil {
                            Text(language.text("home.app_group_warning"))
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                    }
                } header: {
                    Text(language.text("home.status"))
                }

                Section {
                    NavigationLink {
                        GestaltCardsView()
                    } label: {
                        card("home.card.gestalt", detail: "home.card.gestalt_detail", icon: "cpu.fill")
                    }
                    Button { onSelectTab(.files) } label: {
                        card("home.card.files", detail: "home.card.files_detail", icon: "folder.fill")
                    }
                    .buttonStyle(.plain)
                    Button { onSelectTab(.cleaner) } label: {
                        card("home.card.cleaner", detail: "home.card.cleaner_detail", icon: "sparkles")
                    }
                    .buttonStyle(.plain)
                    NavigationLink {
                        BackupCenterView()
                    } label: {
                        card("home.card.backups", detail: "home.card.backups_detail", icon: "externaldrive.fill")
                    }
                    NavigationLink {
                        FileReplaceView()
                    } label: {
                        card("home.card.filereplace", detail: "home.card.filereplace_detail", icon: "arrowshape.replace.forward.fill")
                    }
                } header: {
                    Text(language.text("home.section.data"))
                }

                Section {
                    NavigationLink {
                        AcknowledgementsView()
                    } label: {
                        card("home.card.ack", detail: "home.card.ack_detail", icon: "heart.text.square.fill")
                    }
                    Button(action: onOpenSettings) {
                        card("home.card.settings", detail: "home.card.settings_detail", icon: "gear")
                    }
                    .buttonStyle(.plain)
                } header: {
                    Text(language.text("home.section.about"))
                }
            }
            .listStyle(.insetGrouped)
            .navigationTitle("3106 Lite")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                AppUtilityToolbar(language: language, onOpenSettings: onOpenSettings, onOpenLogs: onOpenLogs)
            }
        }
    }

    private func card(_ titleKey: String, detail: String, icon: String) -> some View {
        HStack(spacing: 12) {
            AppRowIcon(systemName: icon)
            VStack(alignment: .leading, spacing: 2) {
                Text(language.text(titleKey)).foregroundStyle(.primary)
                Text(language.text(detail)).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
    }

    private var appGroupText: String {
        SandboxAccess.appGroup ?? language.text("home.app_group_missing")
    }
}
'''


def apply(root: Path) -> None:
    base = root / 'ThreeOneOSSix'
    app_path = base / 'App.swift'
    app = app_path.read_text(encoding='utf-8')
    app = replace_exact(app, '    @State private var updateOffer: AppUpdateChecker.Offer?\n', '', 'App.updateState')
    app = strip_block(app, '    private func checkForUpdate() {', 'App.launchCheck')
    app = strip_block(app, '    private func checkForUpdateThrottled() {', 'App.foregroundCheck')
    app = strip_block(app, '            .alert(item: $updateOffer) {', 'App.updateAlert')
    app = replace_exact(app, '                        checkForUpdate()\n', '', 'App.onboarding')
    app = replace_exact(app, '                    checkForUpdate()\n', '', 'App.onAppear')
    app = replace_exact(app, '                checkForUpdateThrottled()\n', '', 'App.foregroundCall')
    app_path.write_text(app, encoding='utf-8')

    settings_path = base / 'views/SettingsView.swift'
    settings = settings_path.read_text(encoding='utf-8')
    for state in [
        '    @State private var updateStatus: String?\n',
        '    @State private var updateURL: URL?\n',
        '    @State private var isCheckingUpdate = false\n',
    ]:
        settings = replace_exact(settings, state, '', 'Settings.state')
    settings = strip_block(settings, '    private func checkUpdateManually() {', 'Settings.manual')
    settings = cut_between(
        settings,
        '                Section {\n                    Button {\n                        checkUpdateManually()',
        '                Section {\n                    Toggle(isOn: $experimentalFeaturesEnabled)',
        'Settings.updateSection'
    )
    settings = cut_between(
        settings,
        '                Section {\n                    Toggle(isOn: $experimentalFeaturesEnabled)',
        '                Section(language.text("common.device"))',
        'Settings.advancedSections'
    )
    settings = replace_exact(settings, '    @AppStorage(FeatureVisibility.developerModeStorageKey) private var experimentalFeaturesEnabled = false\n', '', 'Settings.experimentalFlag')
    settings = replace_exact(settings, 'Text("3106").font(.headline)', 'Text("3106 Lite").font(.headline)', 'Settings.name')
    settings_path.write_text(settings, encoding='utf-8')

    checker_path = base / 'helpers/AppUpdateChecker.swift'
    checker = checker_path.read_text(encoding='utf-8')
    checker = replace_block(checker, '    static func checkIgnoringDismissal() async -> Offer? {',
                            '    static func checkIgnoringDismissal() async -> Offer? { nil }', 'Checker.dismissed')
    checker = replace_block(checker, '    static func checkWithOutcome() async -> CheckOutcome {',
                            '    static func checkWithOutcome() async -> CheckOutcome { .upToDate }', 'Checker.manual')
    checker = replace_block(checker, '    static func throttledForegroundCheck() async -> Offer? {',
                            '    static func throttledForegroundCheck() async -> Offer? { nil }', 'Checker.foreground')
    checker = replace_block(checker, '    static func check() async -> Offer? {',
                            '    static func check() async -> Offer? { nil }', 'Checker.check')
    checker = cut_between(checker, '    // Points at the 3106 fork;', '    struct Offer: Identifiable {', 'Checker.urls')
    checker_path.write_text(checker, encoding='utf-8')

    nav_path = base / 'helpers/AppTabNavigationState.swift'
    nav = nav_path.read_text(encoding='utf-8')
    nav = replace_exact(nav,
                        '        [.home, .files, .search, .cleaner, .backup]',
                        '        [.home, .files, .cleaner, .backup]', 'Navigation.visibleTabs')
    nav_path.write_text(nav, encoding='utf-8')

    content_path = base / 'ContentView.swift'
    content = content_path.read_text(encoding='utf-8')
    content = replace_exact(content,
                            '            selectedSections: [.home, .files, .search, .cleaner, .wallpapers],',
                            '            selectedSections: [.home, .files, .cleaner, .backup],', 'Content.selectedSections')
    content = replace_exact(content, '            developerModeEnabled: true', '            developerModeEnabled: false', 'Content.developerMode')
    content = replace_exact(content, '.navigationTitle("3106")', '.navigationTitle("3106 Lite")', 'Content.name')
    content_path.write_text(content, encoding='utf-8')

    hub_path = base / 'views/FeatureHubView.swift'
    if 'struct FeatureHubView: View' not in hub_path.read_text(encoding='utf-8'):
        raise RuntimeError('Unexpected FeatureHubView upstream')
    hub_path.write_text(FEATURE_HUB, encoding='utf-8')

    plist_path = base / 'Info.plist'
    plist = plist_path.read_text(encoding='utf-8')
    plist = replace_exact(plist,
                          '<key>CFBundleDisplayName</key>\n\t<string>3106</string>',
                          '<key>CFBundleDisplayName</key>\n\t<string>3106 Lite</string>', 'Plist.displayName')
    plist_path.write_text(plist, encoding='utf-8')

    verify(root)


def verify(root: Path) -> None:
    base = root / 'ThreeOneOSSix'
    app = (base / 'App.swift').read_text(encoding='utf-8')
    settings = (base / 'views/SettingsView.swift').read_text(encoding='utf-8')
    checker = (base / 'helpers/AppUpdateChecker.swift').read_text(encoding='utf-8')
    hub = (base / 'views/FeatureHubView.swift').read_text(encoding='utf-8')
    tabs = (base / 'helpers/AppTabNavigationState.swift').read_text(encoding='utf-8')
    for name, data, banned in [
        ('App', app, ['checkForUpdate()', 'checkForUpdateThrottled()', '$updateOffer']),
        ('Settings', settings, ['checkUpdateManually()', 'settings.check_update', 'settings.update_header', 'experimentalFeaturesEnabled']),
        ('Checker', checker, ['URLSession.shared', 'api.github.com/repos/QuinnTang74/3106/releases']),
        ('Hub', hub, ['RepositoryNewView(', 'RepositorySourcesView(', 'MigrationView(', 'KeypadThemeView(', 'WallpaperLabView(']),
    ]:
        for token in banned:
            if token in data:
                raise RuntimeError(f'Verification failed: {name} still contains {token}')
    if '[.home, .files, .cleaner, .backup]' not in tabs:
        raise RuntimeError('Lite navigation not found')
    if '3106 Lite' not in (base / 'Info.plist').read_text(encoding='utf-8'):
        raise RuntimeError('Lite display name not found')
    print('PASS: no in-app update calls, no update UI, Lite home and four tabs')


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        sys.exit('Usage: make_3106_lite.py <upstream-source-dir> [--verify]')
    root = Path(sys.argv[1]).resolve()
    if not (root / 'ThreeOneOSSix.xcodeproj').exists():
        sys.exit('Source checkout is missing ThreeOneOSSix.xcodeproj')
    if len(sys.argv) == 3 and sys.argv[2] == '--verify':
        verify(root)
    else:
        apply(root)
