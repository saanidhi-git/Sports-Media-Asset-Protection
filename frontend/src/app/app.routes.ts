import { Routes } from '@angular/router';
import { LoginRegister } from './login-register/login-register';
import { Home } from './home/home';
import { RegisterAsset } from './register-asset/register-asset';
import { AssetDetails } from './asset-details/asset-details';
import { ScanJobNew } from './scan-job-new/scan-job-new';
import { ScanJobsHistory } from './scan-jobs-history/scan-jobs-history';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', component: LoginRegister },
  { path: 'home', component: Home, canActivate: [authGuard] },
  { path: 'register-asset', component: RegisterAsset, canActivate: [authGuard] },
  { path: 'asset/:id', component: AssetDetails, canActivate: [authGuard] },
  { path: 'scan/new', component: ScanJobNew, canActivate: [authGuard] },
  { path: 'scan/history', component: ScanJobsHistory, canActivate: [authGuard] }
];
