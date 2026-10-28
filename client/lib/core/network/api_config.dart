// Copyright (c) 2026 AI Tech Interview authors. All rights reserved.
// Proprietary and confidential. See LICENSE in the project root.

const apiBaseUrl = String.fromEnvironment('API_BASE_URL');

bool get apiEnabled => apiBaseUrl.isNotEmpty;
