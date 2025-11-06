/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Main theme colors
        primary: {
          600: '#D4A03D',
          500: '#FEC74A',
          400: '#FFD966',
          300: '#FFE599',
          200: '#FFF2CC',
          100: '#FFF9E6',
        },
        secondary: {
          600: '#882137',
          500: '#AF2A47',
          400: '#DA6780',
          300: '#E490A2',
          200: '#F5D6DD',
          100: '#FCEEF1',
        },
        neutral: {
          black: '#031C34',
          500: '#5D87A1',
          400: '#9EB7C7',
          300: '#DFE7EC',
          'grey-bg': '#E7E7E8',
          'light-bg': '#F8F7F9',
          white: '#FFFFFF',
        },
        supportive: {
          purple: '#B37AB5',
          blue: '#00B7F1',
          brown: '#BD9868',
          pink: '#EA919D',
          'grey-blue': '#7592C1',
          green: '#2FB66A',
          grey: '#849DAA',
          beige: '#E6D7C8',
          orange: '#E9853C',
          'green-2': '#748992',
        },
      },
      fontFamily: {
        'en-heading': ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
        'en-body': ['Inter', 'SF Pro Text', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
        'cn-heading': ['Noto Sans SC', 'PingFang SC', 'PingFang TC', 'Hiragino Sans GB', 'Source Han Sans SC', 'Microsoft YaHei UI', 'Microsoft YaHei', 'sans-serif'],
        'cn-body': ['Noto Sans SC', 'PingFang SC', 'PingFang TC', 'Hiragino Sans GB', 'Source Han Sans SC', 'Microsoft YaHei UI', 'Microsoft YaHei', 'sans-serif'],
        // UI stacks that prioritize Inter for Latin and fall back to CJK fonts
        'ui-heading': ['Inter', 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB', 'Source Han Sans SC', 'Microsoft YaHei', 'sans-serif'],
        'ui-body': ['Inter', 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB', 'Source Han Sans SC', 'Microsoft YaHei', 'sans-serif'],
        'mono': ['SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', 'monospace']
      },
      // Add font weights separately
      fontWeight: {
        'thin': '200',
        'light': '300',
        'normal': '400',
        'medium': '500',
        'semibold': '600',
        'bold': '700',
        'extrabold': '800'
      },
      fontSize: {
        'headline-xl': '80pt',
        'headline-1': '60pt',
        'headline-2': '60pt',
        'headline-3': '52pt',
        'headline-4': '52pt',
        'headline-5': '40pt',
        'headline-6': '40pt',
        'title-1': '24pt',
        'title-2': '24pt',
        'title-3': '24pt',
        'body': '16pt',
        'body-small': '12pt',
        'number': '20pt',
      },
      fontWeight: {
        'regular': '400',
        'semibold': '600',
        'bold': '700',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}


