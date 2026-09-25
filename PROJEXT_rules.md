Project: LabelPolis



Description:

A mobile app for detecting Legal Metrology packaging violations using image scanning.



Tech Stack:

\- Mobile: Expo React Native with expo-router

\- Backend: Node.js + Express



App Structure:



mobile/app/

\- index.tsx (Home screen)

\- scan.tsx (Scan label screen)

\- result.tsx (Result screen)

\- history.tsx (History screen)



Rules:

\- Always use expo-router for navigation

\- Do NOT create src/app structure

\- Only use mobile/app for screens

\- Keep UI simple, clean, government-style

\- Use Pressable for buttons

\- Use functional React components

\- Keep code readable and minimal



Core Feature:

\- User uploads or scans product label

\- Image is sent to backend

\- Backend detects:

&#x20; - packaging violations

&#x20; - missing information

\- Response must include:

&#x20; - violations list

&#x20; - legal references (rules/acts)

&#x20; - suggestions for correction



UI Guidelines:

\- Minimal design

\- Centered layout

\- Neutral colors (white, blue, gray)

\- No flashy animations



Navigation Flow:

Home → Scan → Result

&#x20;        ↓

&#x20;     History



