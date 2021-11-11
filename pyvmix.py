import numpy as np
import xarray as xr
from ipdb import set_trace as mybreak
      
## Tri Diagonal Matrix Algorithm(a.k.a Thomas algorithm) solver
def TDMAsolver(ac, bc, cc, dc):
  '''
  TDMA solver, a b c d can be NumPy array type or Python list type.
  refer to http://en.wikipedia.org/wiki/Tridiagonal_matrix_algorithm
  '''
  #nf = len(a)     # number of equations
  nf = ac.shape[0]
  #ac, bc, cc, dc = map(np.array, (a, b, c, d))     # copy the array
  for it in range(1, nf):
    mc = ac[it]/bc[it-1]
    bc[it] = bc[it] - mc*cc[it-1] 
    dc[it] = dc[it] - mc*dc[it-1]

  xc = ac
  xc[-1] = dc[-1]/bc[-1]

  for il in range(nf-2, -1, -1):
    xc[il] = (dc[il]-cc[il]*xc[il+1])/bc[il]
  #del bc, cc, dc  # delete variables from memory
  return xc

class Model(object):
    def __init__(self):
        S = self
        # Settings 
        # --------
        # mixing type: choose between 'tke' and 'profile'
        S.kvAv = 'tke'
        
        # --- convective adjustment
        S.conv_adj = False
        S.kv_conv = 1e-1
        
        # --- background mixing
        S.kv_back = 0.
        S.Av_back = 0.
        
        # Physical constants
        # ------------------
        S.grav = 9.81
        S.tAlpha = 2e-4
        S.T0 = 20.
        S.rho0 = 1024.
        S.cp = 4.18e3
        #S.fcor = 1e-4
        S.fcor = 2.*np.pi/86400.

        S.cdrag = 1.2e-3
        S.rho_air = 1.2
        
        # Time stepping
        # --------------
        S.nt = 24*2 * 20
        S.deltaT = 1800.
        S.lsave = 2*3
        
        # TKE parameter
        # -------------
        S.cu = 0.1
        S.cd = 3.75
        S.alpha = 30.
        S.ceps = 0.7
        S.tke_min = 1e-6
        S.Lmix_min = 1e-8
        # bottom drag 0.001-0.003
        S.bottomDragQuadratic = 0.*0.002
        
        # Default plotting
        # ----------------
        S.ylim_hov = [None, None]
        return

    def initialize(self):
        S = self
  
        # Vertical grid
        # -------------
        S.zu = np.concatenate(([0],-S.dz.cumsum()))
        S.zt = 0.5*(S.zu[1:]+S.zu[:-1])
        S.dzt = np.concatenate(([-S.zt[0]],S.zt[:-1]-S.zt[1:],[-S.zu[-1]+S.zt[-1]]))
        
        # Allocate initial variables
        # --------------------------
        S.uvel = np.zeros((S.nz))
        S.vvel = np.zeros((S.nz))
        S.b = np.zeros((S.nz))
        S.tke = np.zeros((S.nz+1))
        S.kv = np.zeros((S.nz+1))
        S.Av = np.zeros((S.nz+1))
        
        # --- mixing profile (for kvAv = 'profile')
        S.kv_prof = np.zeros((S.nz+1))
        S.Av_prof = np.zeros((S.nz+1))
        
        S.Tu_wnd = np.zeros((S.nz))
        S.Tv_wnd = np.zeros((S.nz))
        S.Tu_bot = np.zeros((S.nz))
        S.Tv_bot = np.zeros((S.nz))
        S.Tb_sfl = np.zeros((S.nz))
        
        # Allocate forcing variables
        # --------------------------
        S.wvel = np.zeros((S.nz+1))
        S.dpdx = np.zeros((S.nz))
        S.dpdy = np.zeros((S.nz))
        
        # Allocate output variables
        # -------------------------
        S.nsave = int(S.nt/S.lsave)
        
        # --- time series of profiles
        S.uvel_s = np.zeros((S.nsave,S.nz))
        S.vvel_s = np.zeros((S.nsave,S.nz))
        S.b_s = np.zeros((S.nsave,S.nz))
        S.tke_s = np.zeros((S.nsave,S.nz+1))
        S.kv_s = np.zeros((S.nsave,S.nz+1))
        S.Av_s = np.zeros((S.nsave,S.nz+1))
        S.Lmix_s = np.zeros((S.nsave,S.nz+1))
        S.N2_s = np.zeros((S.nsave,S.nz+1))
        
        # ---- time series vint MKE equation
        S.Tke_cor = np.zeros((S.nsave)) 
        S.Tke_hpr = np.zeros((S.nsave)) 
        S.Tke_wnd = np.zeros((S.nsave)) 
        S.Tke_bot = np.zeros((S.nsave)) 
        S.Tke_vdf = np.zeros((S.nsave)) 
        S.Tke_vds = np.zeros((S.nsave)) 
        S.Tke_vfl = np.zeros((S.nsave)) 
        S.Tke_tot = np.zeros((S.nsave)) 
        
        # --- time series vint TKE equation
        S.Ttke_tot = np.zeros((S.nsave)) 
        S.Ttke_bpr = np.zeros((S.nsave)) 
        S.Ttke_spr = np.zeros((S.nsave)) 
        S.Ttke_dis = np.zeros((S.nsave)) 
        S.Ttke_vdf = np.zeros((S.nsave)) 
        S.Ttke_bck = np.zeros((S.nsave)) 
        
        # --- time series of the forcing
        S.Qsurf_ts = np.zeros((S.nsave))
        S.taux_ts = np.zeros((S.nsave))
        S.tauy_ts = np.zeros((S.nsave))
        return

    def wind_forcing(self, time):
        taux = 0.
        tauy = 0.
        return taux, tauy
    
    def buoyancy_forcing(self, time):
        Qsurf = 0.
        return Qsurf

    def run_model(self):
        S = self
        nt = S.nt
        lsave = S.lsave
        nsave = S.nsave
        zt = S.zt
        zu = S.zu
        dz = S.dz
        dzt = S.dzt

        uvel = S.uvel
        vvel = S.vvel
        b = S.b
        tke = S.tke
        kv = S.kv
        Av = S.Av

        fcor = S.fcor

        Tu_wnd = S.Tu_wnd
        Tv_wnd = S.Tv_wnd
        Tu_bot = S.Tu_bot
        Tv_bot = S.Tv_bot

        Tb_sfl = S.Tb_sfl

        nt = int(nt)
        lsave = int(lsave)

        deltaT = S.deltaT
        nz = S.nz
        
        ls = 0
        for l in range(nt):
          time = l*deltaT
          #if (l%10)==0:
          #  print('l = %d/%d' % (l, nt))
          #taux = taux0#*(1.-np.heaviside(time-10.*86400., 0.) )
          #tauy = tauy0#*(1.-np.heaviside(time-10.*86400., 0.) )
          ##Qsurf = Qsurf0#*(1.-np.heaviside(time-10.*86400., 0.) )
          #Qsurf = Qsurf0*np.sin(2*np.pi*time/86400.)
          taux, tauy = self.wind_forcing(S, time)
          Qsurf = self.buoyancy_forcing(S, time)
        
          # save variables of previous time step
          uvel_old = 1.*uvel
          vvel_old = 1.*vvel
          b_old    = 1.*b
          tke_old  = 1.*tke
        
          # vert derivatives
          N2 = np.zeros((nz+1))
          uz = np.zeros((nz+1))
          vz = np.zeros((nz+1))
          N2[1:-1] = (b[:-1]-b[1:])/dzt[1:-1]
          uz[1:-1] = (uvel[:-1]-uvel[1:])/dzt[1:-1]
          vz[1:-1] = (vvel[:-1]-vvel[1:])/dzt[1:-1]
        
          # paramter
          Ri = N2/(uz+1e-33)
          Pr = np.maximum(1, np.minimum(10., 6.6*Ri))
          S.cb = S.cu/Pr
        
          # mixing length
          Lmix = np.sqrt(2*tke/np.abs(N2+1e-33))
          #Lmix[1:] = np.minimum(Lmix[1:], Lmix[:-1]+dzt[:-1])
          Lmix[0] = 0.
          Lmix[-1] = 0.
          for k in range(1,nz):
            Lmix[k] = np.minimum(Lmix[k], Lmix[k-1]+dzt[k-1])
          Lmix[nz] = np.minimum(Lmix[nz], S.Lmix_min+dzt[nz])
          for k in range(nz-1,1,-1):
            Lmix[k] = np.minimum(Lmix[k], Lmix[k+1]+dzt[k])
          Lmix = np.maximum(Lmix, S.Lmix_min)
        
          # diffusivities
          if S.kvAv=='tke':
            kv = S.cu * tke**0.5*Lmix + S.kv_back
            Av = S.cb * tke**0.5*Lmix + S.Av_back
          elif S.kvAv=='profile':
            kv = 1.*kv_prof + S.kv_back
            Av = 1.*Av_prof + S.Av_back
          if S.conv_adj:
            kv[N2<0] = S.kv_conv
          ktke = S.alpha*0.5*(Av[1:]+Av[:-1])
        
          # ==========
          # tke
          # ==========
          Tt_bpr = -kv*N2
          Tt_spr = Av*(uz**2+vz**2)
        
          # tke diffusion
          """
          dz K dz p = (K(k-1)*(p(k)-p(k-1))/dzw(k-1) - K(k)*(p(k+1)-p(k))/dzw(k))/dzt(k)
            with a(k) = K(k-1)/(dzw(k-1)*dzt(k))
            and  c(k) = K(k)/(dzw(k)*dzt(k))
            and  b(k) = a(k)+c(k)
          dz K dz p = -a(k) p(k-1) + b(k) p(k) - c(k) p(k+1)
          upper BC: a(ks) = 0; b(ks) = c(ks)
          lower BC: c(ks) = 0; b(ks) = a(ks)
          """
          am = np.zeros((nz+1))
          cm = np.zeros((nz+1))
          bm = np.zeros((nz+1))
          am[1:]  = ktke/(dz*dzt[1:])
          cm[:-1] = ktke/(dz*dzt[:-1])
          bm[1:-1] = am[1:-1]+cm[1:-1]
          # ----- upper and lower boundary conditions
          bm[0]    = cm[0]
          bm[-1]   = am[-1]
        
          implicite_tke = True
          tke_bim = 1.*tke
          if implicite_tke:
            # ----- solve tri-diagonal diffusion matrix
            atr = -deltaT*am
            btr = 1+deltaT*bm
            ctr = -deltaT*cm
            dtr = 1.*tke
            dtr += deltaT*(Tt_bpr+Tt_spr)
            # --- adding dissipation
            btr[1:-1] += deltaT*S.ceps*tke[1:-1]**0.5/(Lmix[1:-1]+1e-33)
            tke = TDMAsolver(1.*atr, 1.*btr, 1.*ctr, 1.*dtr)
          #else:
          #  flux = np.zeros((nz+1))
          #  flux = ktke*(tke[:-1]-tke[1:])/dz
          #  Tt_vdf = np.zeros((nz+1))
          #  Tt_vdf[1:-1] = (flux[:-1]-flux[1:])/dzt[1:-1]
          #  Tt_vdf[0]  = (0.       - flux[0])/dzt[0]
          #  Tt_vdf[-1] = (flux[-1] - 0.     )/dzt[-1]
        
          #dz K dz p = -a(k) p(k-1) + b(k) p(k) - c(k) p(k+1)
          Tt_vdf = np.zeros((nz+1))
          Tt_vdf[1:-1] = am[1:-1]*tke[:-2] - bm[1:-1]*tke[1:-1] + cm[1:-1]*tke[2:]
          Tt_vdf[0]  = -bm[0] *tke[0]  + cm[0] *tke[1]
          Tt_vdf[-1] =  am[-1]*tke[-2] - bm[-1]*tke[-1]
          Tt_dis = np.zeros((nz+1))
          Tt_dis[1:-1] = - S.ceps*tke_bim[1:-1]**0.5*tke[1:-1]/(Lmix[1:-1]+1e-33)
        
          Tt     = Tt_bpr + Tt_spr + Tt_dis + Tt_vdf
        
          # ==========
          # hor. vel.
          # ==========
          # velocity tendencies
          impliciteCoriolis = True
          if not impliciteCoriolis:
            Tu_cor = +fcor*vvel
            Tv_cor = -fcor*uvel
          else:
            """
            Implicite Coriolis term: 
            u(l+1)-u(l) =  f dt v(l+1)
            v(l+1)-v(l) = -f dt u(l+1)
            
            u(l+1) - f dt v(l+1) = u(l)
            v(l+1) + f dt u(l+1) = v(l)
            
            |1     - f dt | (u(l+1))   (u(l))
            |f dt    1    | (v(l+1)) = (v(l))
        
            |u(l+1)|                   |1      f dt| |u(l)|
            |      | = 1/(f^2 dt^2+1)  |           | |    |
            |v(l+1)|                   |-f dt  1   | |v(l)|
            """
            tmp = 1./(fcor**2*deltaT**2+1.)
            ulp1 = (uvel + fcor*deltaT*vvel)/(fcor**2*deltaT**2+1.)
            vlp1 = (vvel - fcor*deltaT*uvel)/(fcor**2*deltaT**2+1.)
            Tu_cor = (ulp1-uvel)/deltaT
            Tv_cor = (vlp1-vvel)/deltaT
        
          Tu_hpr = - S.dpdx
          Tv_hpr = - S.dpdy
          Tu_wnd[0] = taux/dz[0]
          Tv_wnd[0] = tauy/dz[0]
          Tu_bot[-1] = -S.bottomDragQuadratic/dz[-1]*np.sqrt(uvel[-1]**2+vvel[-1]**2)*uvel[-1]
          Tv_bot[-1] = -S.bottomDragQuadratic/dz[-1]*np.sqrt(uvel[-1]**2+vvel[-1]**2)*vvel[-1]
          Tu = Tu_cor + Tu_hpr + Tu_wnd + Tu_bot #+ Tu_vdf
          Tv = Tv_cor + Tv_hpr + Tv_wnd + Tv_bot #+ Tv_vdf
        
          # diffusion
          """
          T_diff = d/dz k d/dz p
                 = 1/dz[k] {    A[k]  ( p[k-1]-p[k]   ) / dzt[k] 
                             -  A[k+1]( p[k]  -p[k+1] ) / dzt[k+1] }
                 =    A[k]/(dz[k]*dzt[k]) * p[k-1] 
                   - {A[k]/(dz[k]*dzt[k])+A[k+1]/(dz[k]*dzt[k+1])} * p[k]
                   +  A[k+1]/(dz[k]*dzt[k+1]) * p[k+1]
                 = a[k] * p[k-1] - (a+c)[k] * p[k] + c[k] * p[k+1]
          Neuman:
          k=1:  T_diff = 1/dz[k] { -  A[k+1]( p[k]  -p[k+1] ) / dzt[k+1] } 
          k=nz: T_diff = 1/dz[k] {    A[k]  ( p[k-1]-p[k]   ) / dzt[k]   }
          Dirichlet:
          k=1:  T_diff = -(2*a+b)[k]p[k] + c[k]*p[k+1]
          k=nz: T_diff = a[k]*p[k-1] - (a+2*c)[k]p[k]
          """
          am = Av[:-1]/(dz*dzt[:-1])
          cm = Av[1:] /(dz*dzt[1:])
          bm = am+cm
          bm[0] = cm[0]
          #bm[0] = 2.*am[0]+cm[0] # no-slip
          freeSlipBottom = False
          if freeSlipBottom:   # free-slip
            bm[-1] = am[-1]
          else:                # no-slip
            bm[-1] = am[-1]+2.*cm[-1]
        
          implicite = True
          if implicite:
            # ----- solve tri-diagonal diffusion matrix
            atr = -deltaT*am
            btr = 1+deltaT*bm
            ctr = -deltaT*cm
            # ----- for u
            dtru = 1.*uvel
            dtru += deltaT*(Tu)
            uvel = TDMAsolver(1.*atr, 1.*btr, 1.*ctr, 1.*dtru)
            # ----- for v
            dtrv = 1.*vvel
            dtrv += deltaT*(Tv)
            vvel = TDMAsolver(1.*atr, 1.*btr, 1.*ctr, 1.*dtrv)
        
          Tu_vdf = np.zeros((nz))
          Tu_vdf[1:-1] = am[1:-1]*uvel[:-2] - bm[1:-1]*uvel[1:-1] + cm[1:-1]*uvel[2:]
          Tu_vdf[0]  = -bm[0] *uvel[0]  + cm[0] *uvel[1]
          #Tu_vdf[-1] =  am[-1]*uvel[-2] - bm[-1]*uvel[-1]
          # always add no-slip contribution to bottom tendency
          Tu_vdf[-1] =  am[-1]*uvel[-2] - am[-1]*uvel[-1]
          if not freeSlipBottom:
            Tu_bot[-1] +=  -2.*cm[-1]*uvel[-1]
        
          Tv_vdf = np.zeros((nz))
          Tv_vdf[1:-1] = am[1:-1]*vvel[:-2] - bm[1:-1]*vvel[1:-1] + cm[1:-1]*vvel[2:]
          Tv_vdf[0]  = -bm[0] *vvel[0]  + cm[0] *vvel[1]
          #Tv_vdf[-1] =  am[-1]*vvel[-2] - bm[-1]*vvel[-1]
          # always add no-slip contribution to bottom tendency
          Tv_vdf[-1] =  am[-1]*vvel[-2] - am[-1]*vvel[-1] 
          if not freeSlipBottom:
            Tv_bot[-1] +=  -2.*cm[-1]*vvel[-1]
        
          Tu += Tu_vdf
          Tv += Tv_vdf
        
          # explicite diffusion:  d/dz(k d/dz phi)
          #flux = Av*uz
          #Tu_vdf = (flux[:-1]-flux[1:])/dz
          #flux = Av*vz
          #Tv_vdf = (flux[:-1]-flux[1:])/dz
          #flux = Av*vz
          #Tv_vdf = (flux[:-1]-flux[1:])/dz
        
          # ==========
          # buoycancy
          # ==========
          # buoyancy tendencies
          bi = np.zeros((nz+1))
          bi[1:-1] = 0.5*(b[:-1]+b[1:]) # FIXME: not true for unequal grid spacing
          flux = S.wvel*bi
          Tb_vad = -(flux[:-1]-flux[1:])/dz
          Tb_res = S.lam_b*(S.b0-b)
          #flux = kv*N2
          #Tb_vdf = (flux[:-1]-flux[1:])/dz
          Tb_sfl[0] = S.grav*S.tAlpha/(S.rho0*S.cp)/dz[0]*Qsurf  # for [Qsurf]=W/m^2
          Tb = Tb_vad + Tb_sfl + Tb_res #+ Tb_vdf
        
          # diffusion
          am = kv[:-1]/(dz*dzt[:-1])
          cm = kv[1:] /(dz*dzt[1:])
          bm = am+cm
          bm[0] = cm[0]
          bm[-1] = am[-1]
        
          if implicite:
            # ----- solve tri-diagonal diffusion matrix
            atr = -deltaT*am
            btr = 1+deltaT*bm
            ctr = -deltaT*cm
            # ----- for b
            dtrb = 1.*b
            dtrb += deltaT*(Tb)
            b = TDMAsolver(1.*atr, 1.*btr, 1.*ctr, 1.*dtrb)
        
          Tb_vdf = np.zeros((nz))
          Tb_vdf[1:-1] = am[1:-1]*b[:-2] - bm[1:-1]*b[1:-1] + cm[1:-1]*b[2:]
          Tb_vdf[0]  = -bm[0] *b[0]  + cm[0] *b[1]
          Tb_vdf[-1] =  am[-1]*b[-2] - bm[-1]*b[-1]
        
          Tb += Tb_vdf
        
          # ==========
          # Adams-Bashforth timestepping
          # ==========
          if l==0:
            Tu_old = 1.*Tu
            Tv_old = 1.*Tv
            Tb_old = 1.*Tb
            Tt_old = 1.*Tt
        
          epsab = 0.01
          if not implicite:
            uvel = uvel + deltaT*((1.5+epsab)*Tu - (0.5+epsab)*Tu_old)
            vvel = vvel + deltaT*((1.5+epsab)*Tv - (0.5+epsab)*Tv_old)
            b    = b    + deltaT*((1.5+epsab)*Tb - (0.5+epsab)*Tb_old)
          if not implicite_tke:
            tke  = tke  + deltaT*((1.5+epsab)*Tt - (0.5+epsab)*Tt_old)
        
          tke_before_bck = 1.*tke
          tke[tke<S.tke_min] = S.tke_min
          Tt_bck = (tke-tke_before_bck)/deltaT
        
          Tu_old = 1.*Tu
          Tv_old = 1.*Tv
          Tb_old = 1.*Tb
          Tt_old = 1.*Tt
        
          Tu_tot = (uvel-uvel_old)/deltaT
          Tv_tot = (vvel-vvel_old)/deltaT
          Tb_tot = (b-b_old)/deltaT
          Tt_tot = (tke-tke_old)/deltaT

          S.uvel = uvel
          S.vvel = vvel
          S.b = b
        
          # saving variables
          if (l%lsave)==0:
            print('saving at l = %d / %d: %.1f'%(l, nt, 100.*l/nt))
            S.b_s[ls,:] = b
            S.uvel_s[ls,:] = uvel
            S.vvel_s[ls,:] = vvel
            S.tke_s[ls,:] = tke
            S.kv_s[ls,:] = kv
            S.Av_s[ls,:] = Av
            S.Lmix_s[ls,:] = Lmix
            S.N2_s[ls,:] = N2
        
            S.Tke_cor[ls] = ((ulp1*Tu_cor + vlp1*Tv_cor)*dz).sum()
            S.Tke_hpr[ls] = ((uvel*Tu_hpr + vvel*Tv_hpr)*dz).sum()
            S.Tke_wnd[ls] = ((uvel*Tu_wnd + vvel*Tv_wnd)*dz).sum()
            S.Tke_bot[ls] = ((uvel*Tu_bot + vvel*Tv_bot)*dz).sum()
            S.Tke_vdf[ls] = ((uvel*Tu_vdf + vvel*Tv_vdf)*dz).sum()
            S.Tke_tot[ls] = ((uvel*Tu_tot + vvel*Tv_tot)*dz).sum()
        
            S.Ttke_tot[ls] = (Tt_tot*dzt).sum()
            S.Ttke_bpr[ls] = (Tt_bpr*dzt).sum()
            S.Ttke_spr[ls] = (Tt_spr*dzt).sum()
            S.Ttke_dis[ls] = (Tt_dis*dzt).sum()
            S.Ttke_vdf[ls] = (Tt_vdf*dzt).sum()
            S.Ttke_bck[ls] = (Tt_bck*dzt).sum()
        
            S.Qsurf_ts[ls] = Qsurf
            S.taux_ts[ls] = taux
            S.tauy_ts[ls] = tauy
        
            """
            u d/dz Av d/dz u = d/dz u Av d/dz u - av (d/dz u)^2
        
            """
            tmp = -Av*(uz)**2 - Av*(vz)**2
            S.Tke_vds[ls] = ((0.5*(tmp[1:]+tmp[:-1]))*dz).sum()
            S.Tke_vfl[ls] = ((   uvel*Tu_vdf + vvel*Tv_vdf 
                               - 0.5*(tmp[1:]+tmp[:-1])   )*dz).sum()
        
        
            #mybreak()
            ls += 1
        
        Tt_err = Tt_tot - (Tt_bpr+Tt_spr+Tt_dis+Tt_vdf+Tt_bck)
        Tb_err = Tb_tot - (Tb_vad+Tb_res+Tb_vdf+Tb_sfl)
        Tu_err = Tu_tot - (Tu_cor+Tu_hpr+Tu_wnd+Tu_bot+Tu_vdf)
        Tv_err = Tv_tot - (Tv_cor+Tv_hpr+Tv_wnd+Tv_bot+Tv_vdf)
        
        S.mke_ts = (0.5*(S.uvel_s**2+S.vvel_s**2)*dz[np.newaxis,:]).sum(axis=1)
        S.tke_ts = (S.tke_s*dzt[np.newaxis,:]).sum(axis=1)
        S.uvel_ts = (S.uvel_s*dz[np.newaxis,:]).sum(axis=1)
        S.vvel_ts = (S.vvel_s*dz[np.newaxis,:]).sum(axis=1)
        #ape = (0.5*b_s**2/(N2i+1e-33))*dz[np.newaxis,:]).sum(axis=1)
        S.b2 = (S.b_s**2*dz[np.newaxis,:]).sum(axis=1)
        S.time = deltaT*lsave * np.arange(nsave)
        return
