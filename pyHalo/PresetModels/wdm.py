from pyHalo.Cosmology.geometry import Geometry
from pyHalo.Rendering.SpatialDistributions.nfw import ProjectedNFW
from pyHalo.Rendering.SpatialDistributions.uniform import LensConeUniform
from pyHalo.concentration_models import preset_concentration_models
from pyHalo.mass_function_models import preset_mass_function_models
from pyHalo.pyhalo import pyHalo
from pyHalo.truncation_models import truncation_models


def WDM(z_lens, z_source, log_mc, sigma_sub=0.025, log_mlow=6., log_mhigh=10.,
        mass_function_model_subhalos='LOVELL2020', kwargs_mass_function_subhalos={},
        mass_function_model_fieldhalos='LOVELL2020', kwargs_mass_function_fieldhalos={},
        concentration_model_subhalos='BOSE2016', kwargs_concentration_model_subhalos={},
        concentration_model_fieldhalos='BOSE2016', kwargs_concentration_model_fieldhalos={},
        truncation_model_subhalos='TRUNCATION_ROCHE_GILMAN2020', kwargs_truncation_model_subhalos={},
        truncation_model_fieldhalos='TRUNCATION_RN', kwargs_truncation_model_fieldhalos={},
        shmf_log_slope=-1.9, cone_opening_angle_arcsec=6., log_m_host=13.3, r_tidal=0.25,
        LOS_normalization=1.0, geometry_type='DOUBLE_CONE', kwargs_cosmo=None,
        mdef_subhalos='TNFW', mdef_field_halos='TNFW', kwargs_density_profile={}):

    """
    This class generates realizations of dark matter structure in Warm Dark Matter

    :param z_lens: main deflector redshift
    :param z_source: source redshift
    :param log_mc: the log base 10 of the half-mode mass
    :param sigma_sub: amplitude of the subhalo mass function at 10^8 solar masses in units [# of halos / kpc^2]
    :param log_mlow: log base 10 of the minimum halo mass to render
    :param log_mhigh: log base 10 of the maximum halo mass to render
    :param mass_function_model_subhalos: mass function model for subhalos, see mass_function_models.py for a list
    :param kwargs_mass_function_subhalos: keyword arguments for the mass function model
    :param mass_function_model_fieldhalos: mass function model for field halos, see mass_function_models.py for a list
    :param kwargs_mass_function_fieldhalos: keyword arguments for the mass function model
    :param concentration_model_subhalos: the concentration-mass relation applied to subhalos,
    see concentration_models.py for a complete list of available models
    :param kwargs_concentration_model_subhalos: keyword arguments for the subhalo MC relation
    NOTE: keyword args returned by the load_concentration_model override these keywords with duplicate arguments
    :param concentration_model_subhalos: the concentration-mass relation applied to field halos,
    see concentration_models.py for a complete list of available models
    :param kwargs_concentration_model_fieldhalos: keyword arguments for the field halo MC relation
    NOTE: keyword args returned by the load_concentration_model override these keywords with duplicate arguments
    :param truncation_model_subhalos: the truncation model applied to subhalos, see truncation_models for a complete list
    :param kwargs_truncation_model_subhalos: keyword arguments for the truncation model applied to subhalos
    :param truncation_model_fieldhalos: the truncation model applied to field halos, see truncation_models for a
    complete list
    :param kwargs_truncation_model_fieldhalos: keyword arguments for the truncation model applied to field halos
    :param shmf_log_slope: the logarithmic slope of the subhalo mass function pivoting around 10^8 M_sun
    :param cone_opening_angle_arcsec: the opening angle of the rendering volume in arcsec
    :param log_m_host: log base 10 of the host halo mass [M_sun]
    :param r_tidal: the core radius of the host halo in units of the host halo scale radius. Subhalos are distributed
    in 3D with a cored NFW profile with this core radius
    :param geometry_type: string that specifies the geometry of the rendering volume; options include
    DOUBLE_CONE, CONE, CYLINDER
    :param kwargs_cosmo: keyword arguments that specify the cosmology (see pyHalo.Cosmology.cosmology)
    :param mdef_subhalos: mass definition for subhalos
    :param mdef_field_halos: mass definition for field halos
    :param kwargs_density_profile: keyword arguments for the specified mass profile
    :return: a realization of dark matter halos
    """
    # FIRST WE CREATE AN INSTANCE OF PYHALO, WHICH SETS THE COSMOLOGY
    pyhalo = pyHalo(z_lens, z_source, kwargs_cosmo)
    # WE ALSO SPECIFY THE GEOMETRY OF THE RENDERING VOLUME
    geometry = Geometry(pyhalo.cosmology, z_lens, z_source,
                        cone_opening_angle_arcsec, geometry_type)

    # SET THE SPATIAL DISTRIBUTION MODELS FOR SUBHALOS AND FIELD HALOS:
    subhalo_spatial_distribution = ProjectedNFW
    fieldhalo_spatial_distribution = LensConeUniform

    # SET THE MASS FUNCTION MODELS FOR SUBHALOS AND FIELD HALOS
    # NOTE: MASS FUNCTIONS SHOULD NOT BE INSTANTIATED HERE
    mass_function_model_subhalos, kwargs_mass_function_subhalos = preset_mass_function_models(mass_function_model_subhalos,
                                                                                              kwargs_mass_function_subhalos)
    kwargs_mass_function_subhalos['log_mc'] = log_mc

    mass_function_model_fieldhalos, kwargs_mass_function_fieldhalos = preset_mass_function_models(mass_function_model_fieldhalos,
                                                                                                  kwargs_mass_function_fieldhalos)
    kwargs_mass_function_fieldhalos['log_mc'] = log_mc

    # SET THE CONCENTRATION-MASS RELATION FOR SUBHALOS AND FIELD HALOS
    kwargs_concentration_model_subhalos['cosmo'] = pyhalo.astropy_cosmo
    kwargs_concentration_model_subhalos['log_mc'] = log_mc
    kwargs_concentration_model_fieldhalos['cosmo'] = pyhalo.astropy_cosmo
    kwargs_concentration_model_fieldhalos['log_mc'] = log_mc

    model_subhalos, kwargs_mc_subs = preset_concentration_models(concentration_model_subhalos,
                                                                 kwargs_concentration_model_subhalos)
    concentration_model_CDM = preset_concentration_models('DIEMERJOYCE19')[0]
    kwargs_mc_subs['concentration_cdm_class'] = concentration_model_CDM
    concentration_model_subhalos = model_subhalos(**kwargs_mc_subs)

    model_fieldhalos, kwargs_mc_field = preset_concentration_models(concentration_model_fieldhalos,
                                                                    kwargs_concentration_model_fieldhalos)
    kwargs_mc_field['cosmo'] = pyhalo.astropy_cosmo
    kwargs_mc_field['log_mc'] = log_mc
    concentration_model_CDM = preset_concentration_models('DIEMERJOYCE19')[0]
    kwargs_mc_field['concentration_cdm_class'] = concentration_model_CDM
    concentration_model_fieldhalos = model_fieldhalos(**kwargs_mc_field)
    c_host = concentration_model_fieldhalos.nfw_concentration(10 ** log_m_host, z_lens)

    # SET THE TRUNCATION RADIUS FOR SUBHALOS AND FIELD HALOS
    kwargs_truncation_model_subhalos['lens_cosmo'] = pyhalo.lens_cosmo
    kwargs_truncation_model_fieldhalos['lens_cosmo'] = pyhalo.lens_cosmo

    model_subhalos, kwargs_trunc_subs = truncation_models(truncation_model_subhalos)
    kwargs_trunc_subs.update(kwargs_truncation_model_subhalos)
    if truncation_model_subhalos == 'TRUNCATION_GALACTICUS':
        kwargs_trunc_subs['c_host'] = c_host
    kwargs_trunc_subs['lens_cosmo'] = pyhalo.lens_cosmo
    truncation_model_subhalos = model_subhalos(**kwargs_trunc_subs)

    model_fieldhalos, kwargs_trunc_field = truncation_models(truncation_model_fieldhalos)
    kwargs_trunc_field.update(kwargs_truncation_model_fieldhalos)
    kwargs_trunc_field['lens_cosmo'] = pyhalo.lens_cosmo
    truncation_model_fieldhalos = model_fieldhalos(**kwargs_trunc_field)

    # NOW THAT THE CLASSES ARE SPECIFIED, WE SORT THE KEYWORD ARGUMENTS AND CLASSES INTO LISTS
    population_model_list = ['SUBHALOS', 'LINE_OF_SIGHT', 'TWO_HALO']

    mass_function_class_list = [mass_function_model_subhalos,
                                mass_function_model_fieldhalos,
                                mass_function_model_fieldhalos]
    kwargs_mass_function_subhalos.update({'log_mlow': log_mlow,
                       'log_mhigh': log_mhigh,
                       'm_pivot': 10 ** 8,
                       'power_law_index': shmf_log_slope,
                       'log_m_host': log_m_host,
                       'sigma_sub': sigma_sub,
                       'delta_power_law_index': 0.0})
    kwargs_mass_function_fieldhalos.update({'log_mlow': log_mlow,
                  'log_mhigh': log_mhigh,
                  'LOS_normalization': LOS_normalization,
                  'm_pivot': 10 ** 8,
                  'log_m_host': log_m_host,
                  'delta_power_law_index': 0.0})
    kwargs_mass_function_list = [kwargs_mass_function_subhalos, kwargs_mass_function_fieldhalos, kwargs_mass_function_fieldhalos]
    spatial_distribution_class_list = [subhalo_spatial_distribution, fieldhalo_spatial_distribution, fieldhalo_spatial_distribution]

    kwargs_subhalos_spatial = {'m_host': 10 ** log_m_host, 'zlens': z_lens, 'c_host': c_host,
                               'rmax2d_arcsec': cone_opening_angle_arcsec / 2, 'r_core_units_rs': r_tidal,
                               'lens_cosmo': pyhalo.lens_cosmo, 'c_host': c_host}
    kwargs_los_spatial = {'cone_opening_angle': cone_opening_angle_arcsec, 'geometry': geometry}
    kwargs_spatial_distribution_list = [kwargs_subhalos_spatial, kwargs_los_spatial, kwargs_los_spatial]

    kwargs_halo_model = {'truncation_model_subhalos': truncation_model_subhalos,
                         'concentration_model_subhalos': concentration_model_subhalos,
                         'truncation_model_field_halos': truncation_model_fieldhalos,
                         'concentration_model_field_halos': concentration_model_fieldhalos,
                         'kwargs_density_profile': kwargs_density_profile}

    realization_list = pyhalo.render(population_model_list, mass_function_class_list, kwargs_mass_function_list,
                                     spatial_distribution_class_list, kwargs_spatial_distribution_list,
                                     geometry, mdef_subhalos, mdef_field_halos, kwargs_halo_model, nrealizations=1)
    return realization_list[0]


def WDM_mixed(z_lens, z_source, log_mc, mixed_DM_frac, sigma_sub=0.025, log_mlow=6., log_mhigh=10.,
        mass_function_model_subhalos='SHMF_MIXED_WDM_TURNOVER', kwargs_mass_function_subhalos={},
        mass_function_model_fieldhalos='MIXED_WDM_TURNOVER', kwargs_mass_function_fieldhalos={},
        concentration_model_subhalos='BOSE2016', kwargs_concentration_model_subhalos={},
        concentration_model_fieldhalos='BOSE2016', kwargs_concentration_model_fieldhalos={},
        truncation_model_subhalos='TRUNCATION_ROCHE_GILMAN2020', kwargs_truncation_model_subhalos={},
        truncation_model_fieldhalos='TRUNCATION_RN', kwargs_truncation_model_fieldhalos={},
        shmf_log_slope=-1.9, cone_opening_angle_arcsec=6., log_m_host=13.3, r_tidal=0.25,
        LOS_normalization=1.0, geometry_type='DOUBLE_CONE', kwargs_cosmo=None,
        kwargs_density_profile={}):

    """
    Implements the mixed dark matter model presented by Keely et al. (2023)
    https://arxiv.org/pdf/2301.07265.pdf

    :param z_lens:
    :param z_source:
    :param log_mc:
    :param mixed_DM_frac: fraction of dark matter in CDM component
    :param sigma_sub:
    :param log_mlow:
    :param log_mhigh:
    :param mass_function_model_subhalos:
    :param kwargs_mass_function_subhalos:
    :param mass_function_model_fieldhalos:
    :param kwargs_mass_function_fieldhalos:
    :param concentration_model_subhalos:
    :param kwargs_concentration_model_subhalos:
    :param concentration_model_fieldhalos:
    :param kwargs_concentration_model_fieldhalos:
    :param truncation_model_subhalos:
    :param kwargs_truncation_model_subhalos:
    :param truncation_model_fieldhalos:
    :param kwargs_truncation_model_fieldhalos:
    :param shmf_log_slope:
    :param cone_opening_angle_arcsec:
    :param log_m_host:
    :param r_tidal:
    :param LOS_normalization:
    :param geometry_type:
    :param kwargs_cosmo:
    :param kwargs_density_profile:
    :return:
    """
    params = ['a_wdm', 'b_wdm', 'c_wdm']
    values_keeley_2023 = [0.5, 0.8, -3.0]
    for i, param in enumerate(params):
        if param not in kwargs_mass_function_subhalos.keys():
            kwargs_mass_function_subhalos[param] = values_keeley_2023[i]
        if param not in kwargs_mass_function_fieldhalos.keys():
            kwargs_mass_function_fieldhalos[param] = values_keeley_2023[i]
    kwargs_mass_function_subhalos['mixed_DM_frac'] = mixed_DM_frac
    kwargs_mass_function_fieldhalos['mixed_DM_frac'] = mixed_DM_frac
    kwargs_wdm = {'z_lens': z_lens, 'z_source': z_source, 'log_mc': log_mc, 'sigma_sub': sigma_sub,
                  'log_mlow': log_mlow, 'log_mhigh': log_mhigh,
                  'mass_function_model_subhalos': mass_function_model_subhalos,
                  'kwargs_mass_function_subhalos': kwargs_mass_function_subhalos,
                  'mass_function_model_fieldhalos': mass_function_model_fieldhalos,
                  'kwargs_mass_function_fieldhalos': kwargs_mass_function_fieldhalos,
                  'concentration_model_subhalos': concentration_model_subhalos,
                  'kwargs_concentration_model_subhalos': kwargs_concentration_model_subhalos,
                  'concentration_model_fieldhalos': concentration_model_fieldhalos,
                  'kwargs_concentration_model_fieldhalos': kwargs_concentration_model_fieldhalos,
                  'truncation_model_subhalos': truncation_model_subhalos,
                  'kwargs_truncation_model_subhalos': kwargs_truncation_model_subhalos,
                  'truncation_model_fieldhalos': truncation_model_fieldhalos,
                  'kwargs_truncation_model_fieldhalos': kwargs_truncation_model_fieldhalos,
                  'shmf_log_slope': shmf_log_slope, 'cone_opening_angle_arcsec': cone_opening_angle_arcsec,
                  'log_m_host': log_m_host, 'r_tidal': r_tidal, 'LOS_normalization': LOS_normalization,
                  'geometry_type': geometry_type, 'kwargs_cosmo': kwargs_cosmo,
                  'kwargs_density_profile': kwargs_density_profile
                  }
    return WDM(**kwargs_wdm)


def WDMGeneral(z_lens, z_source, log_mc, dlogT_dlogk, sigma_sub=0.025, log_mlow=6., log_mhigh=10.,
        truncation_model_subhalos='TRUNCATION_GALACTICUS', kwargs_truncation_model_subhalos={},
        truncation_model_fieldhalos='SPLASHBACK', kwargs_truncation_model_fieldhalos={},
        shmf_log_slope=-1.9, cone_opening_angle_arcsec=6., log_m_host=13.3, r_tidal=0.25,
        LOS_normalization=1.0, geometry_type='DOUBLE_CONE', kwargs_cosmo=None,
        mdef_subhalos='TNFW', mdef_field_halos='TNFW', kwargs_density_profile={}):

    """
    This preset model implements a generalized treatment of warm dark matter, or any theory that produces a cutoff in
    the linear matter power spectrum. One additional free parameter is added to parameterize the cutoff in the matter
     power spectrum, dlogT_dlogk, which is the absolute value of the logarithmic derivative of the transfer function
     evaluated at k_1/2, the wavenumber corresponding to the half-mode mass (or log_mc).

     In this model, halo concentrations are computed following the formalism suggeesteed by Schneider et al. (2012) and
     Ludlow et al. (2016), in which the central density of a halo more or less is fully determined by the formation time.

     The mass function is computed from dlogT_dlogk based on the prescription by Stucker et al. (2021)
     https://arxiv.org/pdf/2109.09760.pdf

    :param z_lens: the lens redshift
    :param z_source: source redshift
    :param log_mc: the log (base 10) of the half-mode mass
    :param dlogT_dlogk: the absolute value of the logarithmic derivative of the transfer function at k_1/2; the model
    is calibrated for values between ~1 and ~3
    :param sigma_sub: amplitude of the subhalo mass function
    :param log_mlow: minimum halo mass to render
    :param log_mhigh: maximum halo mass to render
    :param truncation_model_subhalos: the truncation model applied to subhalos, see truncation_models for a complete list
    :param kwargs_truncation_model_subhalos: keyword arguments for the truncation model applied to subhalos
    :param truncation_model_fieldhalos: the truncation model applied to field halos, see truncation_models for a
    complete list
    :param kwargs_truncation_model_fieldhalos: keyword arguments for the truncation model applied to field halos
    :param shmf_log_slope: logarithmic slope of the subhalo mass function
    :param cone_opening_angle_arcsec: the opening angle of the rendering volume
    :param log_m_host: the log (base 10) of the host halo mass
    :param r_tidal: the core size in units of the scale radius of the host halo; subhalos are rendered uniformly in 3D
    inside this radius
    :param LOS_normalization: the amplitude of the LOS mass function relative to Sheth-Tormen
    :param geometry_type: CONE, DOUBLE_CONE, CYLINDER - sets the geometry of the rendering volume
    :param kwargs_cosmo: keyword arguments to set cosmology
    :param mdef_subhalos: mass definition for subhalos
    :param mdef_field_halos: mass definition for field halos
    :param kwargs_density_profile: keyword arguments for the density profile
    :return:
    """
    # FIRST WE CREATE AN INSTANCE OF PYHALO, WHICH SETS THE COSMOLOGY
    pyhalo = pyHalo(z_lens, z_source, kwargs_cosmo)
    # WE ALSO SPECIFY THE GEOMETRY OF THE RENDERING VOLUME
    geometry = Geometry(pyhalo.cosmology, z_lens, z_source,
                        cone_opening_angle_arcsec, geometry_type)

    # SET THE SPATIAL DISTRIBUTION MODELS FOR SUBHALOS AND FIELD HALOS:
    subhalo_spatial_distribution = ProjectedNFW
    fieldhalo_spatial_distribution = LensConeUniform
    kwargs_model_dlogT_dlogk = {'dlogT_dlogk': dlogT_dlogk}
    mass_function_model_subhalos, kwargs_mfunc_subs = preset_mass_function_models('STUCKER_SHMF', kwargs_model_dlogT_dlogk)
    mass_function_model_fieldhalos, kwargs_mfunc_field = preset_mass_function_models('STUCKER', kwargs_model_dlogT_dlogk)
    # SET THE CONCENTRATION-MASS RELATION FOR SUBHALOS AND FIELD HALOS
    concentration_model = 'FROM_FORMATION_HISTORY'
    model_subhalos, kwargs_concentration_model_subhalos = preset_concentration_models(concentration_model,
                                                                                      kwargs_model_dlogT_dlogk)
    concentration_model_CDM = preset_concentration_models('DIEMERJOYCE19')[0]
    kwargs_concentration_model_subhalos['concentration_cdm_class'] = concentration_model_CDM
    kwargs_concentration_model_subhalos['cosmo'] = pyhalo.astropy_cosmo
    kwargs_concentration_model_subhalos['log_mc'] = log_mc
    concentration_model_subhalos = model_subhalos(**kwargs_concentration_model_subhalos)

    model_fieldhalos, kwargs_concentration_model_fieldhalos = preset_concentration_models(concentration_model,
                                                                                          kwargs_model_dlogT_dlogk)
    kwargs_concentration_model_fieldhalos['concentration_cdm_class'] = concentration_model_CDM
    kwargs_concentration_model_fieldhalos['cosmo'] = pyhalo.astropy_cosmo
    kwargs_concentration_model_fieldhalos['log_mc'] = log_mc
    concentration_model_fieldhalos = model_fieldhalos(**kwargs_concentration_model_fieldhalos)
    c_host = concentration_model_fieldhalos.nfw_concentration(10 ** log_m_host, z_lens)
    # SET THE TRUNCATION RADIUS FOR SUBHALOS AND FIELD HALOS
    kwargs_truncation_model_subhalos['lens_cosmo'] = pyhalo.lens_cosmo
    kwargs_truncation_model_fieldhalos['lens_cosmo'] = pyhalo.lens_cosmo
    model_subhalos, kwargs_trunc_subs = truncation_models(truncation_model_subhalos)
    kwargs_trunc_subs.update(kwargs_truncation_model_subhalos)
    if truncation_model_subhalos == 'TRUNCATION_GALACTICUS':
        kwargs_trunc_subs['c_host'] = c_host
    truncation_model_subhalos = model_subhalos(**kwargs_trunc_subs)
    model_fieldhalos, kwargs_trunc_field = truncation_models(truncation_model_fieldhalos)
    kwargs_trunc_field.update(kwargs_truncation_model_fieldhalos)
    truncation_model_fieldhalos = model_fieldhalos(**kwargs_trunc_field)
    # NOW THAT THE CLASSES ARE SPECIFIED, WE SORT THE KEYWORD ARGUMENTS AND CLASSES INTO LISTS
    population_model_list = ['SUBHALOS', 'LINE_OF_SIGHT', 'TWO_HALO']
    mass_function_class_list = [mass_function_model_subhalos,
                                mass_function_model_fieldhalos,
                                mass_function_model_fieldhalos]
    kwargs_mfunc_subs.update({'log_mlow': log_mlow,
                       'log_mhigh': log_mhigh,
                       'm_pivot': 10 ** 8,
                       'power_law_index': shmf_log_slope,
                       'log_m_host': log_m_host,
                       'sigma_sub': sigma_sub,
                       'delta_power_law_index': 0.0,
                        'log_mc': log_mc})
    kwargs_mfunc_field.update({'log_mlow': log_mlow,
                  'log_mhigh': log_mhigh,
                  'LOS_normalization': LOS_normalization,
                  'm_pivot': 10 ** 8,
                  'log_m_host': log_m_host,
                  'delta_power_law_index': 0.0,
                  'log_mc': log_mc})
    kwargs_mass_function_list = [kwargs_mfunc_subs, kwargs_mfunc_field, kwargs_mfunc_field]
    spatial_distribution_class_list = [subhalo_spatial_distribution, fieldhalo_spatial_distribution, fieldhalo_spatial_distribution]
    kwargs_subhalos_spatial = {'m_host': 10 ** log_m_host, 'zlens': z_lens,
                               'rmax2d_arcsec': cone_opening_angle_arcsec / 2, 'r_core_units_rs': r_tidal,
                               'lens_cosmo': pyhalo.lens_cosmo, 'c_host': c_host}
    kwargs_los_spatial = {'cone_opening_angle': cone_opening_angle_arcsec, 'geometry': geometry}
    kwargs_spatial_distribution_list = [kwargs_subhalos_spatial, kwargs_los_spatial, kwargs_los_spatial]

    kwargs_halo_model = {'truncation_model_subhalos': truncation_model_subhalos,
                         'concentration_model_subhalos': concentration_model_subhalos,
                         'truncation_model_field_halos': truncation_model_fieldhalos,
                         'concentration_model_field_halos': concentration_model_fieldhalos,
                         'kwargs_density_profile': kwargs_density_profile}

    realization_list = pyhalo.render(population_model_list, mass_function_class_list, kwargs_mass_function_list,
                                     spatial_distribution_class_list, kwargs_spatial_distribution_list,
                                     geometry, mdef_subhalos, mdef_field_halos, kwargs_halo_model, nrealizations=1)
    return realization_list[0]
