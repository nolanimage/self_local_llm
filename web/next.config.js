/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    RABBITMQ_HOST: process.env.RABBITMQ_HOST || 'localhost',
    RABBITMQ_PORT: process.env.RABBITMQ_PORT || '5672',
    RABBITMQ_USER: process.env.RABBITMQ_USER || 'admin',
    RABBITMQ_PASS: process.env.RABBITMQ_PASS || 'admin123',
  },
}

module.exports = nextConfig
