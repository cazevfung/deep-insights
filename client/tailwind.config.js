import plugin from 'tailwindcss/plugin'

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
      keyframes: {
        'stream-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
        'stream-fade-in': {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'stream-pulse': 'stream-pulse 1.8s ease-in-out infinite',
        'stream-fade-in': 'stream-fade-in 0.2s ease-out',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    plugin(({ addComponents, theme }) => {
      addComponents({
        '.stream-display-container': {
          backgroundColor: theme('colors.neutral.white'),
          borderRadius: theme('borderRadius.lg'),
          border: `1px solid ${theme('colors.neutral.300')}`,
          boxShadow: theme('boxShadow.sm'),
          padding: theme('spacing.6'),
        },
        '.stream-content': {
          position: 'relative',
          backgroundColor: theme('colors.neutral.light-bg'),
          borderRadius: theme('borderRadius.lg'),
          padding: theme('spacing.4'),
          fontFamily: Array.isArray(theme('fontFamily.mono'))
            ? theme('fontFamily.mono').join(',')
            : theme('fontFamily.mono'),
        },
        '.stream-content-text': {
          fontFamily: Array.isArray(theme('fontFamily.mono'))
            ? theme('fontFamily.mono').join(',')
            : theme('fontFamily.mono'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.relaxed'),
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          color: theme('colors.neutral.800'),
        },
        '.stream-content-preview': {
          fontFamily: Array.isArray(theme('fontFamily.mono'))
            ? theme('fontFamily.mono').join(',')
            : theme('fontFamily.mono'),
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.relaxed'),
          color: theme('colors.neutral.500'),
        },
        '.stream-structured': {
          backgroundColor: theme('colors.neutral.light-bg'),
          borderRadius: theme('borderRadius.lg'),
          padding: theme('spacing.4'),
          overflow: 'auto',
        },
        '.stream-structured-view': {
          fontSize: theme('fontSize.sm'),
          lineHeight: theme('lineHeight.relaxed'),
          color: theme('colors.neutral.700'),
        },
        '.stream-tab': {
          display: 'inline-flex',
          alignItems: 'center',
          gap: theme('spacing.1'),
          padding: `${theme('spacing.1')} ${theme('spacing.3')}`,
          borderRadius: theme('borderRadius.full'),
          backgroundColor: 'transparent',
          color: theme('colors.neutral.500'),
          fontSize: theme('fontSize.sm'),
          transitionProperty: 'background-color, color',
          transitionDuration: theme('transitionDuration.150'),
          cursor: 'pointer',
          fontWeight: theme('fontWeight.medium'),
          '&:hover': {
            backgroundColor: theme('colors.neutral.300'),
            color: theme('colors.neutral.600'),
          },
        },
        '.stream-tab-active': {
          backgroundColor: theme('colors.primary.100'),
          color: theme('colors.primary.500'),
          cursor: 'pointer',
        },
        '.stream-raw-container': {
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: theme('colors.neutral.light-bg'),
          borderRadius: theme('borderRadius.xl'),
          border: `1px solid ${theme('colors.neutral.300')}`,
          boxShadow: theme('boxShadow.xs'),
          overflow: 'hidden',
        },
        '.stream-raw-header': {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${theme('spacing.2')} ${theme('spacing.4')}`,
          backgroundColor: theme('colors.neutral.white'),
          borderBottom: `1px solid ${theme('colors.neutral.300')}`,
        },
        '.stream-raw-header-controls': {
          display: 'inline-flex',
          alignItems: 'center',
          gap: theme('spacing.1'),
        },
        '.stream-raw-dot': {
          width: theme('spacing.2'),
          height: theme('spacing.2'),
          borderRadius: theme('borderRadius.full'),
          backgroundColor: theme('colors.neutral.300'),
          boxShadow: `0 0 0 1px ${theme('colors.neutral.white')}`,
        },
        '.stream-raw-dot-red': {
          backgroundColor: theme('colors.secondary.500'),
        },
        '.stream-raw-dot-yellow': {
          backgroundColor: theme('colors.primary.400'),
        },
        '.stream-raw-dot-green': {
          backgroundColor: theme('colors.supportive.green'),
        },
        '.stream-raw-title': {
          fontSize: theme('fontSize.xs'),
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: theme('colors.neutral.500'),
          fontWeight: theme('fontWeight.medium'),
        },
        '.stream-raw-body': {
          backgroundColor: theme('colors.neutral.light-bg'),
          padding: theme('spacing.4'),
          fontFamily: Array.isArray(theme('fontFamily.mono'))
            ? theme('fontFamily.mono').join(',')
            : theme('fontFamily.mono'),
        },
      })
    }),
  ],
}


