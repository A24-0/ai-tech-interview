// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/level.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/widgets/common.dart';
import 'auth_controller.dart';

class AuthPage extends ConsumerStatefulWidget {
  const AuthPage({super.key});

  @override
  ConsumerState<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends ConsumerState<AuthPage> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _signUp = false;
  bool _hidden = true;
  Level _level = Level.middle;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    final controller = ref.read(authControllerProvider.notifier);
    if (_signUp) {
      controller.signUp(_email.text, _password.text, _level);
    } else {
      controller.signIn(_email.text, _password.text, _level);
    }
  }

  void _useDemo() {
    _email.text = 'demo@interview.dev';
    _password.text = 'demo123';
    ref.read(authControllerProvider.notifier).clearError();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final wide = MediaQuery.sizeOf(context).width >= 960;
    return Scaffold(
      backgroundColor: c.background,
      body: Row(
        children: [
          if (wide) const Expanded(child: _HeroPanel()),
          if (wide) VerticalDivider(width: 1, color: c.border),
          Expanded(
            child: Stack(
              children: [
                Align(
                  alignment: Alignment.topRight,
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (wide)
                          Text(
                            'Need help?',
                            style: Theme.of(
                              context,
                            ).textTheme.bodySmall?.copyWith(fontSize: 13),
                          ),
                        if (wide) const SizedBox(width: 20),
                        const _ThemeToggle(),
                      ],
                    ),
                  ),
                ),
                Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 24,
                      vertical: 72,
                    ),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 460),
                      child: _FormCard(
                        email: _email,
                        password: _password,
                        signUp: _signUp,
                        hidden: _hidden,
                        level: _level,
                        onModeChanged: (v) {
                          ref
                              .read(authControllerProvider.notifier)
                              .clearError();
                          setState(() => _signUp = v);
                        },
                        onToggleHidden: () =>
                            setState(() => _hidden = !_hidden),
                        onLevel: (l) => setState(() => _level = l),
                        onSubmit: _submit,
                        onDemo: _useDemo,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 24,
                  child: Text(
                    'By continuing, you agree to the Terms and Privacy Policy.',
                    textAlign: TextAlign.center,
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: c.textFaint),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ThemeToggle extends ConsumerWidget {
  const _ThemeToggle();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = context.colors;
    final dark = ref.watch(themeModeProvider) == ThemeMode.dark;
    return InkWell(
      customBorder: const CircleBorder(),
      onTap: ref.read(themeModeProvider.notifier).toggle,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: c.surface,
          shape: BoxShape.circle,
          border: Border.all(color: c.border),
        ),
        child: Icon(
          dark ? Icons.light_mode_outlined : Icons.wb_sunny_outlined,
          size: 16,
          color: c.textMuted,
        ),
      ),
    );
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel();

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    return Container(
      color: c.background,
      padding: const EdgeInsets.fromLTRB(48, 34, 48, 36),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const BrandMark(),
              const SizedBox(width: 12),
              Text('Interview Studio', style: text.titleMedium),
            ],
          ),
          const Spacer(),
          const Pill(
            'AI technical interview simulator',
            tone: PillTone.success,
            dot: true,
          ),
          const SizedBox(height: 22),
          Text(
            'Practice the interview,\nnot just the problem.',
            style: text.displaySmall?.copyWith(fontSize: 46),
          ),
          const SizedBox(height: 18),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 470),
            child: Text(
              'A focused workspace for realistic dialogue, live coding, and evidence-based feedback tailored to your target level.',
              style: text.bodyLarge?.copyWith(color: c.textMuted, fontSize: 17),
            ),
          ),
          const SizedBox(height: 30),
          const _SamplePrompt(),
          const SizedBox(height: 34),
          Text(
            'Private practice sessions · Feedback generated after every interview',
            style: text.bodySmall?.copyWith(color: c.textFaint),
          ),
        ],
      ),
    );
  }
}

class _SamplePrompt extends StatelessWidget {
  const _SamplePrompt();

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 494),
      child: AppCard(
        radius: 18,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: c.primary,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'Python Core — Middle',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const Spacer(),
                Text(
                  '45:00',
                  style: monoStyle(context, size: 12, color: c.textMuted),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: const BoxDecoration(
                    color: Color(0xFF111111),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.auto_awesome,
                    size: 14,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'Walk me through how you’d find index pairs that sum to a target.',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: c.codeBackground,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                'def find_pairs(nums, target):\n    seen = {}\n    # explain your approach...',
                style: monoStyle(context, size: 12, color: c.codeText),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FormCard extends ConsumerWidget {
  const _FormCard({
    required this.email,
    required this.password,
    required this.signUp,
    required this.hidden,
    required this.level,
    required this.onModeChanged,
    required this.onToggleHidden,
    required this.onLevel,
    required this.onSubmit,
    required this.onDemo,
  });

  final TextEditingController email;
  final TextEditingController password;
  final bool signUp;
  final bool hidden;
  final Level level;
  final ValueChanged<bool> onModeChanged;
  final VoidCallback onToggleHidden;
  final ValueChanged<Level> onLevel;
  final VoidCallback onSubmit;
  final VoidCallback onDemo;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = context.colors;
    final text = Theme.of(context).textTheme;
    final auth = ref.watch(authControllerProvider);
    final hasError = auth.error != null;
    return AppCard(
      radius: 24,
      padding: const EdgeInsets.fromLTRB(32, 32, 32, 26),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            signUp ? 'Create account' : 'Welcome back',
            style: text.headlineMedium,
          ),
          const SizedBox(height: 8),
          Text(
            signUp
                ? 'Start practicing with a realistic AI interviewer.'
                : 'Continue your preparation with a realistic AI interviewer.',
            style: text.bodyMedium?.copyWith(color: c.textMuted),
          ),
          const SizedBox(height: 24),
          _ModeSwitch(signUp: signUp, onChanged: onModeChanged),
          const SizedBox(height: 22),
          Text('Email', style: text.titleSmall),
          const SizedBox(height: 8),
          TextField(
            controller: email,
            keyboardType: TextInputType.emailAddress,
            onChanged: (_) =>
                ref.read(authControllerProvider.notifier).clearError(),
            decoration: InputDecoration(
              hintText: 'you@example.com',
              prefixIcon: Icon(
                Icons.mail_outline,
                size: 18,
                color: c.textMuted,
              ),
              enabledBorder: hasError ? _errorBorder(c) : null,
              focusedBorder: hasError ? _errorBorder(c) : null,
            ),
          ),
          const SizedBox(height: 18),
          Text('Password', style: text.titleSmall),
          const SizedBox(height: 8),
          TextField(
            controller: password,
            obscureText: hidden,
            onChanged: (_) =>
                ref.read(authControllerProvider.notifier).clearError(),
            onSubmitted: (_) => onSubmit(),
            decoration: InputDecoration(
              hintText: signUp ? 'At least 8 characters' : 'Your password',
              prefixIcon: Icon(
                Icons.lock_outline,
                size: 18,
                color: c.textMuted,
              ),
              suffixIcon: IconButton(
                icon: Icon(
                  hidden
                      ? Icons.visibility_off_outlined
                      : Icons.visibility_outlined,
                  size: 18,
                  color: c.textMuted,
                ),
                onPressed: onToggleHidden,
              ),
              enabledBorder: hasError ? _errorBorder(c) : null,
              focusedBorder: hasError ? _errorBorder(c) : null,
            ),
          ),
          if (hasError) ...[
            const SizedBox(height: 14),
            _ErrorBanner(auth.error!),
          ],
          const SizedBox(height: 22),
          Text('Target level', style: text.titleSmall),
          const SizedBox(height: 8),
          Row(
            children: [
              for (final l in Level.values) ...[
                Expanded(
                  child: _LevelChip(
                    level: l,
                    selected: l == level,
                    onTap: () => onLevel(l),
                  ),
                ),
                if (l != Level.values.last) const SizedBox(width: 12),
              ],
            ],
          ),
          const SizedBox(height: 22),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: auth.loading ? null : onSubmit,
              child: auth.loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(signUp ? 'Create account' : 'Sign in'),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: InkWell(
              onTap: onDemo,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.key_outlined, size: 14, color: c.textMuted),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      'Demo account: demo@interview.dev / demo123',
                      overflow: TextOverflow.ellipsis,
                      style: text.bodySmall?.copyWith(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  OutlineInputBorder _errorBorder(AppColors c) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: BorderSide(color: c.danger),
    );
  }
}

class _ModeSwitch extends StatelessWidget {
  const _ModeSwitch({required this.signUp, required this.onChanged});

  final bool signUp;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    Widget tab(String label, bool value) {
      final selected = signUp == value;
      return Expanded(
        child: GestureDetector(
          onTap: () => onChanged(value),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            height: 38,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected ? c.surface : Colors.transparent,
              borderRadius: BorderRadius.circular(9),
              border: selected ? Border.all(color: c.border) : null,
            ),
            child: Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: selected ? c.text : c.textMuted,
              ),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: c.surfaceMuted,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(children: [tab('Sign in', false), tab('Sign up', true)]),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: c.dangerTint,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline, size: 16, color: c.danger),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(fontSize: 12.5, color: c.danger, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _LevelChip extends StatelessWidget {
  const _LevelChip({
    required this.level,
    required this.selected,
    required this.onTap,
  });

  final Level level;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final c = context.colors;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: onTap,
      child: Container(
        height: 40,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? c.primaryTint : c.surface,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: selected ? c.primary : c.border),
        ),
        child: Text(
          level.label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: selected ? c.primaryStrong : c.textMuted,
          ),
        ),
      ),
    );
  }
}
