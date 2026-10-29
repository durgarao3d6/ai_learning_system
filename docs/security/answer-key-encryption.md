# Security: Answer Key Encryption

## 1. What is Answer Key Encryption?
In LearnSmart, each question generated for a quiz contains a correct answer and an explanation. If these are stored as plain text in the database and inadvertently included in API payloads sent to the client during an exam, inspecting the browser network tab or local memory exposes the answers, compromising the integrity of the quiz.

To prevent this, answer keys and explanations are encrypted symmetrically at rest using **Fernet** (`cryptography.fernet.Fernet`), an authenticated symmetric encryption system based on 128-bit AES in CBC mode with PKCS7 padding, HMAC-SHA256 authentication, and a timestamp.

## 2. Why Fernet?
1. **Authenticated Encryption with Associated Data (AEAD) / Integrity Protection**:
   Fernet guarantees that ciphertext cannot be read or altered without the encryption key. Tampering with the ciphertext causes decryption to raise an `InvalidToken` error.
2. **Standard & Well-Tested**:
   Fernet is part of Python's standard `cryptography` library, ensuring constant-time operations and avoiding custom cryptographic pitfalls.
3. **Deterministic Structure**:
   Fernet tokens include a version byte, a 64-bit timestamp, a 16-byte IV, AES-128 ciphertext, and a 32-byte HMAC tag.

## 3. Key Management Architecture
- **Quiz-Specific or Global Encryption Key**:
  `FERNET_SECRET_KEY` is loaded from `app.config.Settings` (or generated deterministically / configured per deployment).
- **Decryption Lifecycle**:
  - **During Quiz Taking (`GET /api/v1/quizzes/{id}`)**: Answer keys and explanations are completely stripped from the response payload. The client receives only `question_id`, `text`, `type`, and `options`.
  - **During Grading (`POST /api/v1/attempts/{id}/submit`)**: The backend decrypts `answer_key_encrypted` in-memory strictly within the grading service to compare against the student's submitted answers.
  - **During Results Review (`GET /api/v1/attempts/{id}/results`)**: Only after an attempt is marked `completed` or `auto_submitted` are the decrypted answers and explanations returned to the client.

## 4. Threat Model & Mitigations
- **Threat 1: Student inspects network responses**:
  - *Mitigation*: The quiz endpoint serializes a projection schema (`QuestionPublicResponse`) that excludes the encrypted answer field entirely.
- **Threat 2: SQL dump / read replica compromised**:
  - *Mitigation*: Even with raw database read access, answer keys cannot be derived without the application's encryption key.
