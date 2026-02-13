import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // You can later send this to Sentry / LogRocket
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-blue-900 px-6">
          <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-lg text-center">
            <h2 className="text-2xl font-black text-red-600 mb-4">
              🚨 Something went wrong
            </h2>

            <p className="text-gray-700 mb-6">
              An unexpected error occurred while rendering the application.
              Please try again.
            </p>

            <button
              onClick={this.handleRetry}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-3 px-6 rounded-xl transition-all"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
