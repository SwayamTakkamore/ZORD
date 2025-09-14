import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../services/storage_service.dart';
import 'debug_screen.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _biometricEnabled = false;
  bool _notificationsEnabled = true;
  bool _darkMode = false;
  int _refreshInterval = 30;
  PackageInfo? _packageInfo;

  @override
  void initState() {
    super.initState();
    _loadSettings();
    _loadPackageInfo();
  }

  void _loadSettings() {
    setState(() {
      _biometricEnabled = StorageService.getBiometricEnabled();
      _notificationsEnabled = StorageService.getNotificationsEnabled();
      _darkMode = StorageService.getDarkMode();
      _refreshInterval = StorageService.getRefreshInterval();
    });
  }

  Future<void> _loadPackageInfo() async {
    final packageInfo = await PackageInfo.fromPlatform();
    setState(() {
      _packageInfo = packageInfo;
    });
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        children: [
          // User Profile Section
          _buildSection(
            title: 'Profile',
            children: [
              ListTile(
                leading: const CircleAvatar(
                  child: Icon(Icons.person),
                ),
                title: Text(authState.user?.username ?? 'User'),
                subtitle: Text(authState.user?.email ?? ''),
                trailing: const Icon(Icons.chevron_right),
              ),
            ],
          ),

          // Security Section
          _buildSection(
            title: 'Security',
            children: [
              SwitchListTile(
                title: const Text('Biometric Authentication'),
                subtitle: const Text('Use fingerprint or face ID to login'),
                value: _biometricEnabled,
                onChanged: (value) async {
                  await StorageService.setBiometricEnabled(value);
                  setState(() {
                    _biometricEnabled = value;
                  });
                },
                secondary: const Icon(Icons.fingerprint),
              ),
              ListTile(
                leading: const Icon(Icons.lock_outline),
                title: const Text('Change Password'),
                subtitle: const Text('Update your account password'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // TODO: Implement password change
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Password change - coming soon'),
                    ),
                  );
                },
              ),
            ],
          ),

          // Notifications Section
          _buildSection(
            title: 'Notifications',
            children: [
              SwitchListTile(
                title: const Text('Push Notifications'),
                subtitle: const Text('Receive alerts for high-risk transactions'),
                value: _notificationsEnabled,
                onChanged: (value) async {
                  await StorageService.setNotificationsEnabled(value);
                  setState(() {
                    _notificationsEnabled = value;
                  });
                },
                secondary: const Icon(Icons.notifications_outlined),
              ),
            ],
          ),

          // Appearance Section
          _buildSection(
            title: 'Appearance',
            children: [
              SwitchListTile(
                title: const Text('Dark Mode'),
                subtitle: const Text('Use dark theme'),
                value: _darkMode,
                onChanged: (value) async {
                  await StorageService.setDarkMode(value);
                  setState(() {
                    _darkMode = value;
                  });
                  // TODO: Implement theme switching
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Theme change will take effect after restart'),
                    ),
                  );
                },
                secondary: const Icon(Icons.dark_mode_outlined),
              ),
            ],
          ),

          // Data & Storage Section
          _buildSection(
            title: 'Data & Storage',
            children: [
              ListTile(
                leading: const Icon(Icons.refresh),
                title: const Text('Auto-refresh Interval'),
                subtitle: Text('${_refreshInterval}s'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showRefreshIntervalDialog(),
              ),
              ListTile(
                leading: const Icon(Icons.clear_all),
                title: const Text('Clear Cache'),
                subtitle: const Text('Remove locally stored data'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showClearCacheDialog(),
              ),
              ListTile(
                leading: const Icon(Icons.bug_report, color: Colors.orange),
                title: const Text('Debug & Health Check'),
                subtitle: const Text('Test backend connectivity'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const DebugScreen(),
                    ),
                  );
                },
              ),
            ],
          ),

          // About Section
          _buildSection(
            title: 'About',
            children: [
              ListTile(
                leading: const Icon(Icons.info_outline),
                title: const Text('App Version'),
                subtitle: Text(_packageInfo?.version ?? 'Loading...'),
              ),
              ListTile(
                leading: const Icon(Icons.description_outlined),
                title: const Text('Terms of Service'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // TODO: Show terms of service
                },
              ),
              ListTile(
                leading: const Icon(Icons.privacy_tip_outlined),
                title: const Text('Privacy Policy'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // TODO: Show privacy policy
                },
              ),
              ListTile(
                leading: const Icon(Icons.help_outline),
                title: const Text('Help & Support'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // TODO: Show help & support
                },
              ),
            ],
          ),

          // Logout Section
          _buildSection(
            title: 'Account',
            children: [
              ListTile(
                leading: const Icon(Icons.logout, color: Colors.red),
                title: const Text(
                  'Logout',
                  style: TextStyle(color: Colors.red),
                ),
                onTap: () => _showLogoutDialog(),
              ),
            ],
          ),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
          child: Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Theme.of(context).primaryColor,
            ),
          ),
        ),
        Card(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(children: children),
        ),
      ],
    );
  }

  void _showRefreshIntervalDialog() {
    final intervals = [5, 10, 15, 30, 60, 120];
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Auto-refresh Interval'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: intervals.map((interval) {
            return RadioListTile<int>(
              title: Text('${interval}s'),
              value: interval,
              groupValue: _refreshInterval,
              onChanged: (value) async {
                await StorageService.setRefreshInterval(value!);
                setState(() {
                  _refreshInterval = value;
                });
                Navigator.pop(context);
              },
            );
          }).toList(),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _showClearCacheDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Cache'),
        content: const Text(
          'This will remove all locally stored transaction data. Are you sure?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              await StorageService.clearTransactionCache();
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Cache cleared successfully'),
                ),
              );
            },
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  void _showLogoutDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Logout'),
        content: const Text('Are you sure you want to logout?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
            },
            child: const Text('Logout'),
          ),
        ],
      ),
    );
  }
}
