"""
This module contains the Visualization class.

This class contains methods for visualizing smoothed particle
hydrodynamics simulations.
"""

import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable

from ..core.particles import I_GAS
from ..core.utils import normalize_vector, rotate_vector_arbitrary_axis
from .interpolation import scalar_interpolation, vector_interpolation
from .options import DEFAULT_OPTIONS


class Visualization:
    """
    Visualize a dump as a particle plot, a rendered plot, or a
    vector plot.

    Parameters
    ----------
    dump : Dump object
        The plonk.Dump object to visualize.

    render : str, default ``None``
        Scalar quantity to render.

    vector : str, default ``None``
        Vector quantity to be represented as arrows or stream
        function.

    Other Parameters
    ----------------
    particle_type : int, default I_GAS
        Particle type to plot, as an int.
    particle_types : collection of int
        Particle types to plot, as a collection of ints.

    xrange : list or tuple of float (len=2), default ``None``
        The range of values for the horizontal (x) axis.
    yrange : list or tuple of float (len=2), default ``None``
        The range of values for the vertical (y) axis.
    extent : list or tuple of float (len=4), default ``None``
        Specify the x and y image range as [xmin, xmax, ymin, ymax].

    rotation_axis : list of float (len=3), default ``None``
        A 3-dimensional vector specifying an axis around which to
        rotate the reference frame. Must also specify
        ``rotation_angle``.
    rotation_angle : float, default ``None``
        An angle (radians) to rotate the reference frame around a
        ``rotation_axis``.
    position_angle : float, default ``None``
        An angle (radians) East of North specifying an axis around
        which to incline the reference frame as specified by
        ``inclination``.
    inclination : float, default ``None``
        An angle (radians) of inclination specified relative to a
        ``position_angle``.

    render_scale : str, default 'linear'
        Render scale options include: 'log', 'linear'.
    render_min : float, default None
        Minimum value of the rendered quantity.
    render_max : float, default None
        Maximum value of the rendered quantity.
    render_fraction_max : float, default None
        Maximum value of the rendered quantity specified as a
        fraction of the maximum in the data.

    stream : bool, default False
        If true, plot vector plots as stream functions.
    stride : int, default 25
        Striding through vector interpolation for vector plots.
    vector_color : str, default None
        Color of vector field as arrows or streamfunction.

    axis : Axes, default None
        Matplotlib Axes object to plot to.
    colorbar : bool, default True
        If true, plot colorbar.
    colormap : str, default 'gist_heat'
        Specify the colormap.
    figure : Figure, default None
        Matplotlib Figure to add Axes to.
    font_family : str, default 'sans-serif'
        Font family style for axes title, label, etc.
    font_size : int, default 12
        Font size for axes title, label, etc.
    title : str, default None
        Plot title.

    accelerate : bool, default False
        Use accelerated interpolation.
    cross_section : bool, default False
        If true, plot a cross section rather than column density
        with slice position specified by ``slice_position``.
    density_weighted : bool, default False
        Use density weighted interpolation.
    distance_to_screen : float, default 0.0
        Distance to screen.
    normalize : bool, default False
        Use normalized interpolation.
    number_pixels : list of float (len=2), default (512, 512)
        The number of pixels in the horizontal and vertical
        directions, like [npixx, npixy], for interpolation. This
        determines the resolution of the image.
    opacity : bool, default False
        Use opacity rendering.
    slice_position : float, 0.0
        Position of the cross sectional slice.
    z_observer : float, default 0.0
        Z position of observer.

    Examples
    --------
    Rendering density.
    >>> viz = plonk.Visualization(dump, render='density')

    Plotting velocity vectors.
    >>> viz = plonk.Visualization(dump, vector='velocity')

    Rotate frame around arbitrary vector.
    >>> viz.rotate_frame(vector=[1, 0, 0], angle=np.pi/2)

    Set image window size.
    >>> viz.set_image_size([-150, 150, -150, 150])

    Set particle type.
    >>> I_DUST = 7
    >>> viz.set_particle_type(I_DUST)

    Set rendered quantity range.
    >>> viz.set_render_range(vmin=0, vmax=1e-7)
    """

    def __init__(self, dump, render=None, vector=None, **kwargs):

        # TODO: physical units
        # TODO: calculated extra quantities

        self._figure_options = dict(DEFAULT_OPTIONS.FigureOptions._asdict())
        for key, value in kwargs.items():
            if key in self._figure_options.keys():
                self._figure_options[key] = value

        self._image_range_options = dict(
            DEFAULT_OPTIONS.ImageRangeOptions._asdict()
        )
        for key, value in kwargs.items():
            if key in self._image_range_options.keys():
                self._image_range_options[key] = value

        self._interpolation_options = dict(
            DEFAULT_OPTIONS.InterpolationOptions._asdict()
        )
        for key, value in kwargs.items():
            if key in self._interpolation_options.keys():
                self._interpolation_options[key] = value

        self._render_options = dict(DEFAULT_OPTIONS.RenderOptions._asdict())
        for key, value in kwargs.items():
            if key in self._render_options.keys():
                self._render_options[key] = value

        self._rotation_options = dict(DEFAULT_OPTIONS.RotationOptions._asdict())
        for key, value in kwargs.items():
            if key in self._rotation_options.keys():
                self._rotation_options[key] = value

        self._vector_options = dict(DEFAULT_OPTIONS.VectorOptions._asdict())
        for key, value in kwargs.items():
            if key in self._vector_options.keys():
                self._vector_options[key] = value

        self._initialized = False

        self._dump = dump
        self._particles = dump.particles
        self._sinks = dump.sinks
        self._header = dump.header

        self.axis = kwargs.get('axis', None)
        self.figure = kwargs.get('figure', None)
        if self.axis is None and self.figure is None:
            plt.clf()
            self.figure = plt.gcf()
        if self.axis is None:
            self.axis = self.figure.gca()
        if self.figure is None:
            self.figure = self.axis.get_figure()

        self._render = None
        self._vector = None
        self._plot_particles = False
        self._plot_render = False
        self._plot_vector = False
        if render is None and vector is None:
            self._plot_particles = True
        if render is not None:
            self._render = render
            self._plot_render = True
        if vector is not None:
            self._vector = vector
            self._plot_vector = True

        self._available_particle_types = set(
            np.unique(self._particles.itype[:])
        )
        particle_type = kwargs.get('particle_type', None)
        particle_types = kwargs.get('particle_types', None)
        if particle_types is None and particle_type is not None:
            particle_types = particle_type
        self.set_particle_type(particle_types)

        self._init_frame_rotation()
        self.set_image_size()
        self._make_plot()

        self._initialized = True

    def _quantity(self, quantity, mask=None, transform=None):
        if transform is not None:
            func = transform['func']
            args = transform['args']
            if mask is not None:
                return func(quantity[mask], *args)
            return func(quantity, *args)
        if mask is not None:
            return quantity[mask]
        return quantity

    @property
    def _interpolation_weights(self):
        """Interpolation weights."""
        if self._interpolation_options['density_weighted']:
            return np.array(self._particle_mass / self._h ** 2)
        return np.full_like(self._h, 1 / self._header['hfact'])

    @property
    def _particle_mass(self):
        return self._dump.mass

    @property
    def _xyz(self):
        return self._quantity(
            self._particles.xyz[:], self._particle_mask, self._rotation
        )

    @property
    def _x(self):
        return self._xyz[:, 0]

    @property
    def _y(self):
        return self._xyz[:, 1]

    @property
    def _z(self):
        return self._xyz[:, 2]

    @property
    def _h(self):
        return self._quantity(
            self._particles.h[:], self._particle_mask, self._rotation
        )

    @property
    def _vxyz(self):
        return self._quantity(
            self._particles.vxyz[:], self._particle_mask, self._rotation
        )

    @property
    def _vx(self):
        return self._vxyz[:, 0]

    @property
    def _vy(self):
        return self._vxyz[:, 1]

    @property
    def _vz(self):
        return self._vxyz[:, 2]

    def _make_plot(self):

        if self._plot_render:
            self._render_image()

        if self._plot_vector:
            self._vector_image()

        if self._plot_particles:
            self._particle_scatter_plot()

        self._set_axis()
        self.set_axis_labels()
        self.set_title()

    def set_render_scale(self, render_scale=None):
        """
        Set render scale.

        Parameters
        ----------
        render_scale : str
            A string representing the render color scale, e.g.
            'linear' or 'log'.
        """

        if render_scale is None:
            render_scale = 'linear'

        if render_scale == 'log':
            norm = colors.SymLogNorm(1e-1 * self._vmax, clip=True)
        elif render_scale == 'linear':
            norm = colors.Normalize(vmin=self._vmin, vmax=self._vmax, clip=True)
        else:
            raise ValueError("Unknown color render_scale: " + render_scale)

        self._norm = norm
        self._render_scale = render_scale

        if self._initialized:
            self.image.set_norm(norm)
            self._make_colorbar()

    def set_render_range(self, vmin=None, vmax=None):
        """
        Set render range for colorbar.

        Parameters
        ----------
        vmin : float
            Minimum for the render colorbar.
        vmax : float
            Maximum for the render colorbar.
        """
        if vmin is not None and vmax is not None:
            self.image.set_clim(vmin=vmin, vmax=vmax)
            self._vmin, self._vmax = vmin, vmax
        if vmin is not None:
            self.image.set_clim(vmin=vmin)
            self._vmin = vmin
        if vmax is not None:
            self.image.set_clim(vmax=vmax)
            self._vmax = vmax

    def set_particle_type(self, particle_types):
        """
        Set particle type(s) to visualize.

        Parameters
        ----------
        particle_types : int or container of ints
            Integer or container of integers representing the particle
            type.
        """

        if particle_types is None:
            particle_types = I_GAS

        if isinstance(particle_types, int):
            particle_types = set((particle_types,))
        elif isinstance(particle_types, (list, set, tuple)):
            particle_types = set(particle_types)

        if not particle_types.issubset(self._available_particle_types):
            print(f'Some of particle type {particle_types} not available')
            return

        if hasattr(self, '_particle_types'):
            if particle_types == self._particle_types:
                print(f'Particle types {particle_types} already plotted')
                return

        self._particle_types = particle_types
        self._particle_mask = np.logical_or.reduce(
            [self._particles.itype[:] == i for i in particle_types]
        )

        if self._initialized:
            self._make_plot()

    def set_image_size(self, extent=None, size=None):
        """
        Set image size.

        Parameters
        ----------
        extent : list or numpy.ndarray
            Extent is the image size: [xmin, xmax, ymin, ymax].
        size : float
            Extent specified by a single value:
            [-size, size, -size, size].
        """

        if extent is not None:
            if hasattr(self, '_extent'):
                if np.all(extent == self._extent):
                    print(f'Image window size already = {extent}')
                    return
            self._extent = extent
            if self._initialized:
                self._make_plot()
            return
        if size is not None:
            if hasattr(self, '_extent'):
                if np.all(size == np.abs(self._extent)):
                    print(
                        'Image window size already = '
                        f'[-{size}, {size}, -{size}, {size}]'
                    )
                    return
            self._extent = [-size, size, -size, size]
            if self._initialized:
                self._make_plot()
            return

        self._extent = None

        _xrange = self._image_range_options['xrange']
        _yrange = self._image_range_options['yrange']
        _extent = self._image_range_options['extent']

        if _extent is not None:
            if _xrange is not None or _yrange is not None:
                raise ValueError(
                    'Cannot set extent and xrange/yrange at the same time'
                )
            if len(_extent) == 4:
                self._extent = _extent

        if self._extent is None:
            if _xrange is None and _yrange is None:
                _min = self._xyz[:, 0:2].min(axis=0)
                _max = self._xyz[:, 0:2].max(axis=0)
                self._extent = (_min[0], _max[0], _min[1], _max[1])
            else:
                if _xrange is None:
                    _x = (self._x.min(), self._x.max())
                if _yrange is None:
                    _y = (self._y.min(), self._y.max())
                if self._extent is None:
                    self._extent = _x + _y

    def _render_image(self):

        if self._render in ['rho', 'dens', 'density']:
            render_data = self._dump.density[self._particle_mask]
        elif self._render == 'x':
            render_data = self._x
        elif self._render == 'y':
            render_data = self._y
        elif self._render == 'z':
            render_data = self._z
        elif self._render == 'vx':
            render_data = self._vx
        elif self._render == 'vy':
            render_data = self._vy
        elif self._render == 'vz':
            render_data = self._vz
        elif self._render in ['v', 'velocity']:
            render_data = self._particles.extra_quantity('velocity magnitude')[
                self._particle_mask
            ]
        else:
            try:
                render_data = self._particles.arrays[self._render][
                    self._particle_mask
                ]
            except Exception:
                raise ValueError(
                    f'Cannot determine quantity to render: {self._render}'
                )
            if render_data.ndim != 1:
                raise ValueError(f'{self._render} is not 1-dimensional')

        print(f'Rendering {self._render} using Splash')

        image_data = scalar_interpolation(
            self._xyz,
            self._h,
            self._interpolation_weights,
            render_data,
            self._particle_mass,
            self._extent[:2],
            self._extent[2:],
            self._interpolation_options['number_pixels'],
            self._interpolation_options['cross_section'],
            self._interpolation_options['slice_position'],
            self._interpolation_options['opacity'],
            self._interpolation_options['normalize'],
            self._interpolation_options['z_observer'],
            self._interpolation_options['distance_to_screen'],
            self._interpolation_options['accelerate'],
        )

        self._render_image_matplotlib(image_data)

    def _render_image_matplotlib(self, image_data):

        if self._render_options['render_max'] is None:
            vmax = image_data.max()
        else:
            vmax = self._render_options['render_max']
        if self._render_options['render_fraction_max'] is not None:
            vmax = (
                image_data.max() * self._render_options['render_fraction_max']
            )
        if self._render_options['render_min'] is None:
            vmin = image_data.min()
        else:
            vmin = self._render_options['render_min']
        self._vmin, self._vmax = vmin, vmax

        self.set_render_scale(self._render_options['render_scale'])

        self._cmap = self._figure_options['colormap']

        self.image = self.axis.imshow(
            image_data,
            norm=self._norm,
            origin='lower',
            extent=self._extent,
            cmap=self._cmap,
        )

        if not hasattr(self, 'colorbar'):
            if self._figure_options['colorbar']:
                self._make_colorbar()
            else:
                self.colorbar = None
        else:
            self._make_colorbar()

    def _set_render_label(self):
        self._render_label = r'$\int$ ' + f'{self._render}' + ' dz'
        if self._render_scale == 'log':
            self._render_label = ' '.join(('log', self._render_label))

    def _make_colorbar(self):
        if hasattr(self, 'colorbar'):
            self.colorbar.remove()
        divider = make_axes_locatable(self.axis)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        self.colorbar = self.figure.colorbar(self.image, cax=cax)
        self._set_render_label()
        if self._render_label is not None:
            self.colorbar.set_label(self._render_label)

    def _vector_image(self):

        if self._vector in ['v', 'vel', 'velocity']:
            try:
                vector_data = self._vxyz
            except Exception:
                raise ValueError('Velocity not available in dump')
        else:
            try:
                vector_data = self._particles.arrays[self._vector][
                    self._particle_mask
                ]
                if vector_data.ndim != 2 and vector_data.shape[1] != 3:
                    raise ValueError(
                        f'{self._vector} does not have appropriate dimensions'
                    )
            except Exception:
                raise ValueError(
                    f'Cannot determine vector quantity to plot: {self._vector}'
                )

        print(f'Plotting vector field {self._vector} using Splash')

        _xrange, _yrange = self._extent[:2], self._extent[2:]

        vector_data = vector_interpolation(
            self._xyz,
            self._h,
            self._interpolation_weights,
            vector_data,
            _xrange,
            _yrange,
            self._interpolation_options['number_pixels'],
            self._interpolation_options['cross_section'],
            self._interpolation_options['slice_position'],
            self._interpolation_options['normalize'],
            self._interpolation_options['z_observer'],
            self._interpolation_options['distance_to_screen'],
        )

        xvector_data = vector_data[0]
        yvector_data = vector_data[1]

        X, Y = np.meshgrid(
            np.linspace(*_xrange, len(xvector_data)),
            np.linspace(*_yrange, len(yvector_data)),
        )

        vector_color = self._vector_options['vector_color']
        if self._render:
            vector_color = 'white'

        stride = self._vector_options['stride']

        self.stream = None
        self.quiver = None
        if self._vector_options['stream']:
            self.stream = self.axis.streamplot(
                X[::stride, ::stride],
                Y[::stride, ::stride],
                xvector_data[::stride, ::stride],
                yvector_data[::stride, ::stride],
                color=vector_color,
            )
        else:
            self.quiver = self.axis.quiver(
                X[::stride, ::stride],
                Y[::stride, ::stride],
                xvector_data[::stride, ::stride],
                yvector_data[::stride, ::stride],
                color=vector_color,
            )

        self.axis.set_aspect('equal', 'box')

    def _particle_scatter_plot(self):
        marker_size = 0.01
        self.axis.scatter(self._x, self._y, s=marker_size, c='k')
        self.axis.set_aspect('equal', 'box')

    def _init_frame_rotation(self):
        rotation_axis = self._rotation_options.get('rotation_axis', None)
        rotation_angle = self._rotation_options.get('rotation_angle', None)
        position_angle = self._rotation_options.get('position_angle', None)
        inclination = self._rotation_options.get('inclination', None)
        self._rotate_frame = False

        if (rotation_axis is not None or rotation_angle is not None) and (
            position_angle is not None and inclination is not None
        ):
            raise ValueError(
                'Cannot set rotation_axis/rotation_angle and '
                + ' position_angle/inclination at the same time'
            )

        if rotation_axis is not None:
            if rotation_angle is not None:
                self._rotate_frame = True
                rotation_axis = normalize_vector(rotation_axis)
            else:
                raise ValueError('Must specify rotation_angle')
            if isinstance(rotation_axis, list):
                rotation_axis = np.array(rotation_axis)
            rotation_axis = normalize_vector(rotation_axis)

        if rotation_angle is not None and rotation_axis is None:
            raise ValueError('Must specify rotation_axis')

        if position_angle is not None:
            if inclination is not None:
                self._rotate_frame = True
                rotation_angle = inclination
                rotation_axis = np.array(
                    [np.cos(position_angle), np.sin(position_angle), 0]
                )
            else:
                raise ValueError('Must specify inclination')

        if inclination is not None and position_angle is None:
            raise ValueError('Must specify position_angle')

        self.rotate_frame(rotation_axis, rotation_angle)

    def rotate_frame(self, rotation_axis, rotation_angle):
        """
        Rotate viewing frame.

        Specify an axis of rotation and an angle to rotate. This
        rotation is a tranformation on the original frame specified
        in the data.

        Parameters
        ----------
        rotation_axis : list or numpy.ndarray
            Rotation axis for frame rotation as a vector [x, y, z].
        rotation_angle : float
            Rotation angle in radians for frame rotation.
        """

        if rotation_axis is None or rotation_angle is None:
            self._rotation = None
            return
        else:
            self._rotation = {
                'func': rotate_vector_arbitrary_axis,
                'args': (rotation_axis, rotation_angle),
            }

        if hasattr(self, '_rotation_axis') and hasattr(self, '_rotation_angle'):
            if (
                np.all(np.array(rotation_axis) == self._rotation_axis)
                and rotation_angle == self._rotation_angle
            ):
                print(f'Frame already has the specified rotation')
                return

        if rotation_axis is not None and rotation_angle is not None:
            self._rotation_axis = rotation_axis
            self._rotation_angle = rotation_angle

        print(
            f'Rotating {rotation_angle*180/np.pi:.0f} deg around '
            f'[{rotation_axis[0]:.2f},'
            f' {rotation_axis[1]:.2f},'
            f' {rotation_axis[2]:.2f}]'
        )

        if self._initialized:
            self._make_plot()

    def _set_axis(self):

        self.axis.set_xlim(self._extent[0], self._extent[1])
        self.axis.set_ylim(self._extent[2], self._extent[3])

    def set_axis_labels(self, xlabel=None, ylabel=None):
        """
        Set axis labels.

        Parameters
        ----------
        xlabel : str
            Label for the x axis.
        ylabel : str
            Label for the y axis.
        """

        if not self._rotate_frame:
            self.axis.set_xlabel('x')
            self.axis.set_ylabel('y')

        if xlabel is not None:
            self.axis.set_xlabel(xlabel)
        if ylabel is not None:
            self.axis.set_ylabel(ylabel)

    def set_title(self, title=None):
        """
        Set title.

        Parameters
        ----------
        title : str
            Figure title.
        """

        if title is None:
            title = self._figure_options.get('title', None)

        if title is not None:
            self.axis.set_title(title)
