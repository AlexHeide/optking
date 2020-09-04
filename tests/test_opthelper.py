#! optimization of water using optHelper and explicit loop.
#  1. Showing how to use external gradient.
#  2. optking still has a module level parameters and history,
#       that could be eliminated, so not yet multi-object safe.
#  3. Have not yet restarted from json or disk, but should be close to working.
import psi4
import optking

def test_optHelper():
    h2o = psi4.geometry("""
         O
         H 1 1.0
         H 1 1.0 2 104.5
    """)

    psi4.core.clean_options()
    psi4_options = {
      'diis': False,
      'basis': 'sto-3g',
      'e_convergence': 10,
      'd_convergence': 10,
      'scf_type': 'pk',
    }
    psi4.set_options(psi4_options)

    opt = optking.optHelper('hf')
    opt.build_coordinates()
    
    for step in range(30):
        opt.energy_gradient_hessian()
        opt.step()
        conv = opt.testConvergence()
        if conv == True:
            print("Optimization SUCCESS:")
            break
    else:
        print("Optimization FAILURE:\n")
     
    # print(opt.history.summary_string())
    json_output = opt.close()

    E = json_output['energies'][-1] #TEST

    nucenergy = json_output['trajectory'][-1]['properties']['nuclear_repulsion_energy']
    refnucenergy =   8.9064983474  #TEST
    refenergy    = -74.9659011923  #TEST
    assert psi4.compare_values(refnucenergy, nucenergy, 3, "Nuclear repulsion energy")
    assert psi4.compare_values(refenergy, E, 6, "Reference energy")


def test_lj_external_gradient():
    h2o = psi4.geometry("""
         O
         H 1 1.0
         H 1 1.0 2 104.5
    """)
    
    psi4.core.clean_options()
    psi4_options = {
      'basis': 'sto-3g',
      'g_convergence': 'gau_verytight',
    }
    psi4.set_options(psi4_options)
    
    opt = optking.optHelper('hf',comp_type='user')
    opt.build_coordinates()
    
    for step in range(30):
        # Compute one's own energy and gradient
        E, gX = optking.lj_functions.calc_energy_and_gradient(opt.geom, 2.5, 0.01, True)
        # Insert these values into the 'user' computer.
        opt.computer.external_energy = E
        opt.computer.external_gradient = gX

        opt.energy_gradient_hessian()
        opt.step()
        conv = opt.testConvergence()
        if conv == True:
            print("Optimization SUCCESS:")
            break
    else:
        print("Optimization FAILURE:\n")
     
    # print(opt.history.summary_string())
    json_output = opt.close()

    assert conv == True 
    E = json_output['energies'][-1] #TEST
    RefEnergy =  -0.03  # - epsilon * 3, where -epsilon is depth of each Vij well
    assert psi4.compare_values(RefEnergy, E, 6, "L-J Energy upon optimization")

