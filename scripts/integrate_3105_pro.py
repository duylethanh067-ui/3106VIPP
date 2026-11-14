#!/usr/bin/env python3
"""3105 Pro: restore YangJiiii v2 navigation on the pinned 3106 3.2.5 engine.

This changes UI and branding only. It does not add an exploit, relax an iOS
version gate, disable backup protections, or change any signing identity.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def replace_one(data: str, old: str, new: str, description: str) -> str:
    count = data.count(old)
    if count != 1:
        raise RuntimeError(f"{description}: expected 1 match, got {count}")
    return data.replace(old, new, 1)


def integrate(engine: Path, original: Path) -> None:
    src = engine / 'ThreeOneOSSix'
    ref = original / 'ThreeOneOSFive'
    content_path = src / 'ContentView.swift'
    nav_path = src / 'helpers/AppTabNavigationState.swift'
    home_path = src / 'views/RepositoryHomeView.swift'
    plist_path = src / 'Info.plist'
    theme_source = ref / 'views/DesignSystem.swift'
    icon_source = ref / 'Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png'
    theme_target = src / 'views/DesignSystem.swift'
    icon_target = src / 'Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png'
    paths = (content_path, nav_path, home_path, plist_path, theme_source, icon_source)
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"Missing expected pinned upstream file: {path}")

    content = content_path.read_text(encoding='utf-8')
    content = replace_one(content,
        '    @State private var showLogs = false\n',
        '    @State private var showLogs = false\n'
        '    @State private var showTools = false\n'
        '    @State private var showCleaner = false\n'
        '    @State private var showBackup = false\n'
        '    @State private var showWallpapers = false\n',
        'ContentView state')
    content = replace_one(content,
        '        .sheet(isPresented: $showLogs) { LogView() }\n',
        '''        .sheet(isPresented: $showLogs) { LogView() }
        .sheet(isPresented: $showTools) {
            FeatureHubView(
                onSelectTab: openToolSection,
                onOpenSettings: { showTools = false; openSettings() },
                onOpenLogs: { showTools = false; openLogs() }
            )
        }
        .sheet(isPresented: $showCleaner) {
            CleanerView(onOpenSettings: openSettings)
        }
        .sheet(isPresented: $showBackup) { BackupTabView() }
        .sheet(isPresented: $showWallpapers) {
            WallpaperLabView(onOpenSettings: openSettings, onOpenLogs: openLogs)
        }
''',
        'ContentView tool sheets')
    content = replace_one(content,
        '            .navigationTitle("3106")',
        '            .navigationTitle("3105 Pro")',
        'ContentView large layout title')
    content = replace_one(content,
        '''        case .home:
            FeatureHubView(
                onSelectTab: { section in
                    tabNavigation.select(section.rawValue)
                },
                onOpenSettings: openSettings,
                onOpenLogs: openLogs
            )''',
        '''        case .home:
            RepositoryHomeView(
                onOpenSettings: openSettings,
                onOpenLogs: openLogs,
                onOpenTools: { showTools = true }
            )''',
        'ContentView restore 3105 home')
    content = replace_one(content,
        '            selectedSections: [.home, .files, .search, .cleaner, .wallpapers],',
        '            selectedSections: [.home, .sources, .installed, .files, .search],',
        'ContentView tab selection')
    content = replace_one(content,
        '''    private func openSettings() {
        showSettings = true
    }
''',
        '''    private func openToolSection(_ section: AppSection) {
        showTools = false
        switch section {
        case .cleaner:
            showCleaner = true
        case .backup:
            showBackup = true
        case .wallpapers:
            showWallpapers = true
        case .new:
            tabNavigation.select(AppSection.sources.rawValue)
        default:
            tabNavigation.select(section.rawValue)
        }
    }

    private func openSettings() {
        showSettings = true
    }
''',
        'ContentView route tools')

    nav = nav_path.read_text(encoding='utf-8')
    nav = replace_one(nav,
        '        case .home: return "tab.features"',
        '        case .home: return "tab.home"',
        'Navigation home localization')
    nav = replace_one(nav,
        '        case .home: return "square.grid.2x2.fill"',
        '        case .home: return "house.fill"',
        'Navigation home icon')
    nav = replace_one(nav,
        '        [.home, .files, .search, .cleaner, .backup]',
        '        [.home, .sources, .installed, .files, .search]',
        'Navigation visible sections')

    home = home_path.read_text(encoding='utf-8')
    home_head, marker, home_tail = home.partition('struct RepositoryNewView: View')
    if not marker or 'struct RepositoryHomeView: View' not in home_head:
        raise RuntimeError('Unexpected 3106 home view structure')
    home = replace_one(home_head,
        '''    let onOpenSettings: () -> Void
    let onOpenLogs: () -> Void

    var body: some View {''',
        '''    let onOpenSettings: () -> Void
    let onOpenLogs: () -> Void
    let onOpenTools: () -> Void

    var body: some View {''',
        'RepositoryHomeView tool callback')
    home = replace_one(home,
        '            .navigationTitle("3106")',
        '            .navigationTitle("3105 Pro")',
        'RepositoryHomeView title')
    home = replace_one(home,
        '''                    onOpenLogs: onOpenLogs
                )
            }
            .navigationDestination(for: RepositoryPackageRecord.self)''',
        '''                    onOpenLogs: onOpenLogs
                )
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: onOpenTools) {
                        Image(systemName: "square.grid.2x2.fill")
                    }
                    .accessibilityLabel("Additional tools")
                }
            }
            .navigationDestination(for: RepositoryPackageRecord.self)''',
        'RepositoryHomeView tools button')
    home = home + marker + home_tail

    plist = plist_path.read_text(encoding='utf-8')
    plist = replace_one(plist,
        '<key>CFBundleDisplayName</key>\n\t<string>3106</string>',
        '<key>CFBundleDisplayName</key>\n\t<string>3105 Pro</string>',
        'Display name')

    # Validate all transformed files before writing any changes.
    assert 'onSelectTab: openToolSection' in content
    assert 'RepositoryHomeView(' in content
    assert 'onOpenTools: { showTools = true }' in content
    assert '[.home, .sources, .installed, .files, .search]' in nav
    assert 'supportsWorseQuery' in (src / 'helpers/SupportPolicy.swift').read_text(encoding='utf-8')
    assert 'minor <= 3' in (src / 'helpers/SupportPolicy.swift').read_text(encoding='utf-8')
    assert 'enum AppTheme' in theme_source.read_text(encoding='utf-8')
    for lang in ('vi', 'en'):
        strings = (src / f'{lang}.lproj/Localizable.strings').read_text(encoding='utf-8')
        assert '"tab.home" =' in strings
        assert '"tab.sources" =' in strings
        assert '"tab.installed" =' in strings

    content_path.write_text(content, encoding='utf-8')
    nav_path.write_text(nav, encoding='utf-8')
    home_path.write_text(home, encoding='utf-8')
    plist_path.write_text(plist, encoding='utf-8')
    shutil.copy2(theme_source, theme_target)
    shutil.copy2(icon_source, icon_target)
    verify(engine)
    print('PASS: YangJiiii 3105 UI, 3106 backend, 27.3 gate preserved')


def verify(engine: Path) -> None:
    src = engine / 'ThreeOneOSSix'
    content = (src / 'ContentView.swift').read_text(encoding='utf-8')
    nav = (src / 'helpers/AppTabNavigationState.swift').read_text(encoding='utf-8')
    home = (src / 'views/RepositoryHomeView.swift').read_text(encoding='utf-8')
    support = (src / 'helpers/SupportPolicy.swift').read_text(encoding='utf-8')
    checks = {
        '3105 home': 'RepositoryHomeView(' in content,
        'Tools retained': 'FeatureHubView(' in content and 'onSelectTab: openToolSection' in content,
        'Visible tabs': '[.home, .sources, .installed, .files, .search]' in nav,
        'Repository tab': 'case .sources:' in content,
        'Installed tab': 'case .installed:' in content,
        'File tab': 'case .files:' in content,
        'Search tab': 'case .search:' in content,
        'Backup': 'BackupTabView()' in content,
        'Cleaner': 'CleanerView(onOpenSettings: openSettings)' in content,
        'Wallpaper': 'WallpaperLabView(' in content,
        'Device support gate unchanged': 'minor <= 3' in support,
        'Tools home button': 'Button(action: onOpenTools)' in home,
        'Display name': '3105 Pro' in (src / 'Info.plist').read_text(encoding='utf-8'),
        'Localization': '"tab.home" =' in (src / 'vi.lproj/Localizable.strings').read_text(encoding='utf-8'),
    }
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'FAIL'}: {name}")
    if not all(checks.values()):
        raise RuntimeError('Failed source integration checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('original', type=Path, nargs='?')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(args.engine.resolve())
    else:
        if args.original is None:
            parser.error('original 3105 reference directory is required')
        integrate(args.engine.resolve(), args.original.resolve())
