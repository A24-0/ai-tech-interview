# Interview Studio: Flutter client

Web and Windows client of AI Tech Interview. The screens follow the design: sign in and sign up, dashboard, interview setup, live interview with the code editor and test console, assessment report and the admin question bank.

Stack: Riverpod, go_router. Folder layout: `lib/features/<feature>/{data,domain,presentation}`, shared code in `lib/core`.

The data layer currently uses in-memory mock repositories, so the app runs without the server. Demo accounts: `demo@interview.dev` / `demo123` (candidate) and `admin@interview.dev` / `admin123` (admin).

```bash
cd client
flutter pub get
flutter run -d chrome
flutter test
flutter build web
```
