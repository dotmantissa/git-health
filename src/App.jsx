import { useEffect, useMemo, useState } from 'react';
import { Contract } from 'ethers';
import WalletBar from './components/WalletBar';
import RepoInput from './components/RepoInput';
import ScoreGauge from './components/ScoreGauge';
import HistoryList from './components/HistoryList';
import { ABI, CHAIN_ID, CONTRACT_ADDRESS } from './constants';
import { useWallet } from './hooks/useWallet';

function truncateError(message) {
  if (!message) return 'Unknown error';
  return message.length > 120 ? `${message.slice(0, 120)}...` : message;
}

function isValidGithubUrl(url) {
  return url.startsWith('https://github.com/');
}

export default function App() {
  const {
    provider,
    signer,
    address,
    isConnected,
    wrongNetwork,
    chainId,
    walletError,
    connect,
    disconnect,
    switchToGenLayer,
    clearError
  } = useWallet();

  const [repoUrl, setRepoUrl] = useState('');
  const [validationError, setValidationError] = useState('');
  const [inlineError, setInlineError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!inlineError && !walletError) return undefined;
    const timer = setTimeout(() => {
      setInlineError('');
      clearError();
    }, 6000);
    return () => clearTimeout(timer);
  }, [inlineError, walletError, clearError]);

  const gateError = useMemo(() => {
    if (!isConnected) return 'Connect your wallet before interacting with the contract.';
    if (chainId !== CHAIN_ID) return 'Wrong network. Switch to GenLayer Studio to continue.';
    return '';
  }, [isConnected, chainId]);

  const resetAppState = () => {
    setRepoUrl('');
    setValidationError('');
    setInlineError('');
    setLoading(false);
    setLoadingStep(0);
    setSelectedEntry(null);
    setHistory([]);
  };

  const handleDisconnect = () => {
    disconnect();
    resetAppState();
  };

  const validateInput = () => {
    if (!isValidGithubUrl(repoUrl.trim())) {
      setValidationError('Must be a valid github.com URL');
      return false;
    }
    setValidationError('');
    return true;
  };

  const pushHistory = (entry) => {
    setHistory((prev) => [entry, ...prev]);
    setSelectedEntry(entry);
  };

  const handleAnalyze = async () => {
    setInlineError('');
    clearError();

    if (!validateInput()) return;
    if (gateError) {
      setInlineError(gateError);
      return;
    }

    let statusInterval;
    try {
      setLoading(true);
      setLoadingStep(0);
      statusInterval = setInterval(() => {
        setLoadingStep((prev) => (prev + 1) % 3);
      }, 4000);

      setLoadingStep(0);
      const contract = new Contract(CONTRACT_ADDRESS, ABI, signer);
      const tx = await contract.analyze_repo(repoUrl.trim());
      setLoadingStep(1);
      await tx.wait();
      setLoadingStep(2);

      const readContract = new Contract(CONTRACT_ADDRESS, ABI, provider);
      const rawScore = await readContract.get_score(repoUrl.trim());
      const score = Number(rawScore);

      const entry = {
        url: repoUrl.trim(),
        score,
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      if (error?.code === 4001 || error?.code === 'ACTION_REJECTED') {
        setInlineError('Transaction rejected.');
      } else if (
        String(error?.message || '').toLowerCase().includes('network') ||
        String(error?.message || '').toLowerCase().includes('failed to fetch')
      ) {
        setInlineError('RPC connection failed — is GenLayer Studio running?');
      } else {
        setInlineError(truncateError(error?.message || 'Transaction failed.'));
      }
    } finally {
      clearInterval(statusInterval);
      setLoading(false);
    }
  };

  const handleGetCached = async () => {
    setInlineError('');
    clearError();

    if (!validateInput()) return;
    if (gateError) {
      setInlineError(gateError);
      return;
    }

    try {
      const contract = new Contract(CONTRACT_ADDRESS, ABI, provider);
      const score = await contract.get_score(repoUrl.trim());
      const entry = {
        url: repoUrl.trim(),
        score: Number(score),
        timestamp: new Date().toISOString()
      };
      pushHistory(entry);
    } catch (error) {
      if (
        String(error?.message || '').toLowerCase().includes('network') ||
        String(error?.message || '').toLowerCase().includes('failed to fetch')
      ) {
        setInlineError('RPC connection failed — is GenLayer Studio running?');
      } else {
        setInlineError(truncateError(error?.message));
      }
    }
  };

  const activeError = inlineError || walletError;

  return (
    <div className="app-shell">
      <WalletBar
        isConnected={isConnected}
        address={address}
        chainId={chainId}
        wrongNetwork={wrongNetwork}
        onConnect={connect}
        onDisconnect={handleDisconnect}
        onSwitch={switchToGenLayer}
      />

      <hr className="divider" />

      <main className="main-column">
        <RepoInput
          repoUrl={repoUrl}
          onChange={(value) => {
            setRepoUrl(value);
            setValidationError('');
            setInlineError('');
            clearError();
          }}
          onAnalyze={handleAnalyze}
          onGetCached={handleGetCached}
          loading={loading}
          validationError={validationError}
          loadingStep={loadingStep}
        />

        {activeError ? <p className="error-banner">{activeError}</p> : null}

        <ScoreGauge entry={selectedEntry} />

        <HistoryList history={history} onSelect={setSelectedEntry} />
      </main>
    </div>
  );
}
