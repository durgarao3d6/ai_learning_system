import { client } from './client'

export interface UserResponse {
  id: string
  email: string
  role: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type?: string
  user: UserResponse
}

export async function register(email: string, password: string): Promise<TokenResponse> {
  const response = await client.post<TokenResponse>('/api/v1/auth/register', {
    email,
    password,
  })
  return response.data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await client.post<TokenResponse>('/api/v1/auth/login', {
    email,
    password,
  })
  return response.data
}

export async function refresh(refreshToken: string): Promise<{ access_token: string }> {
  const response = await client.post<{ access_token: string }>('/api/v1/auth/refresh', {
    refresh_token: refreshToken,
  })
  return response.data
}

export async function getMe(): Promise<UserResponse> {
  const response = await client.get<UserResponse>('/api/v1/auth/me')
  return response.data
}
